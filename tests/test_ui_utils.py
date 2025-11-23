import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Import gptcli first (with stubs from test_gptcli)
import importlib
import types

# Stub required Rich components so we don't need the real dependency during tests
rich_module = types.ModuleType("rich")
rich_console = types.ModuleType("rich.console")
rich_markdown = types.ModuleType("rich.markdown")
rich_progress = types.ModuleType("rich.progress")
rich_live = types.ModuleType("rich.live")

class DummyConsole:
    def print(self, *args, **kwargs):
        pass

class DummyMarkdown(str):
    def __new__(cls, text):
        return str.__new__(cls, text)

class DummyProgress:
    def __init__(self, *args, **kwargs):
        pass
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False
    def add_task(self, *args, **kwargs):
        return 1

class DummyLive:
    def __init__(self, *args, **kwargs):
        pass
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False
    def update(self, *args, **kwargs):
        pass

rich_console.Console = DummyConsole
rich_markdown.Markdown = DummyMarkdown
rich_progress.Progress = DummyProgress
rich_progress.SpinnerColumn = lambda *args, **kwargs: None
rich_progress.TextColumn = lambda *args, **kwargs: None
rich_progress.TimeElapsedColumn = lambda *args, **kwargs: None
rich_live.Live = DummyLive

sys.modules["rich"] = rich_module
sys.modules["rich.console"] = rich_console
sys.modules["rich.markdown"] = rich_markdown
sys.modules["rich.progress"] = rich_progress
sys.modules["rich.live"] = rich_live

# Stub OpenAI client
openai_module = types.ModuleType("openai")
class DummyAPIError(Exception):
    def __init__(self, message="error", *args, **kwargs):
        super().__init__(message)
        self.message = message
class DummyOpenAI:
    def __init__(self, *args, **kwargs):
        pass
    class responses:
        @staticmethod
        def create(*args, **kwargs):
            raise NotImplementedError
openai_module.OpenAI = DummyOpenAI
openai_module.APIError = DummyAPIError
sys.modules["openai"] = openai_module

# Stub gnureadline
gnureadline_module = types.ModuleType("gnureadline")
def dummy_set_history_length(*args, **kwargs):
    pass
def dummy_set_auto_history(*args, **kwargs):
    pass
gnureadline_module.set_history_length = dummy_set_history_length
gnureadline_module.set_auto_history = dummy_set_auto_history
sys.modules["gnureadline"] = gnureadline_module

# Ensure dummy API key
os.environ.setdefault("OPENAI_API_KEY", "test-key")

# Import gptcli
gptcli = importlib.import_module("gptcli")

# Now import UI utils directly without going through ui/__init__.py
# This avoids importing ui.app which requires Textual
import importlib.util
utils_path = os.path.join(os.path.dirname(__file__), '..', 'ui', 'utils.py')
spec = importlib.util.spec_from_file_location("ui_utils", utils_path)
ui_utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ui_utils)

get_available_chats = ui_utils.get_available_chats
format_chat_entry = ui_utils.format_chat_entry


class TestUIUtils(unittest.TestCase):
	"""Tests for UI utility functions."""
	
	def setUp(self):
		"""Set up test environment."""
		self.test_dir = tempfile.mkdtemp()
		self.conversations_dir = os.path.join(self.test_dir, "conversations")
		os.makedirs(self.conversations_dir)
	
	def tearDown(self):
		"""Clean up test environment."""
		shutil.rmtree(self.test_dir)
	
	def test_get_available_chats_empty(self):
		"""Test getting chats when directory doesn't exist."""
		original_dir = gptcli.CONVERSATIONS_DIR
		try:
			gptcli.CONVERSATIONS_DIR = self.test_dir + "/nonexistent"
			chats = get_available_chats()
			self.assertEqual(chats, [])
		finally:
			gptcli.CONVERSATIONS_DIR = original_dir
	
	def test_get_available_chats_no_chats(self):
		"""Test getting chats when directory exists but is empty."""
		original_dir = gptcli.CONVERSATIONS_DIR
		try:
			gptcli.CONVERSATIONS_DIR = self.conversations_dir
			chats = get_available_chats()
			self.assertEqual(chats, [])
		finally:
			gptcli.CONVERSATIONS_DIR = original_dir
	
	def test_get_available_chats_ignores_config_files(self):
		"""Test that config files are ignored."""
		# Create a config file
		config_file = os.path.join(self.conversations_dir, "test.config.json")
		with open(config_file, 'w') as f:
			json.dump({"model": "gpt-5.1"}, f)
		
		original_dir = gptcli.CONVERSATIONS_DIR
		try:
			gptcli.CONVERSATIONS_DIR = self.conversations_dir
			chats = get_available_chats()
			self.assertEqual(chats, [])
		finally:
			gptcli.CONVERSATIONS_DIR = original_dir
	
	def test_get_available_chats_ignores_directories(self):
		"""Test that directories are ignored."""
		# Create a subdirectory
		subdir = os.path.join(self.conversations_dir, "subdir")
		os.makedirs(subdir)
		
		original_dir = gptcli.CONVERSATIONS_DIR
		try:
			gptcli.CONVERSATIONS_DIR = self.conversations_dir
			chats = get_available_chats()
			self.assertEqual(chats, [])
		finally:
			gptcli.CONVERSATIONS_DIR = original_dir
	
	def test_get_available_chats_loads_chats(self):
		"""Test loading available chats."""
		# Create a conversation file
		chat_file = os.path.join(self.conversations_dir, "test_chat.json")
		with open(chat_file, 'w') as f:
			json.dump([
				{"role": "user", "content": "Hello"},
				{"role": "assistant", "content": "Hi"}
			], f)
		
		original_dir = gptcli.CONVERSATIONS_DIR
		try:
			gptcli.CONVERSATIONS_DIR = self.conversations_dir
			with patch.object(gptcli, 'load_chat_config', return_value={"model": "gpt-5.1"}), \
				 patch.object(gptcli, 'load_conversation', return_value=[
					 {"role": "user", "content": "Hello"},
					 {"role": "assistant", "content": "Hi"}
				 ]):
				chats = get_available_chats()
				self.assertEqual(len(chats), 1)
				self.assertEqual(chats[0]["name"], "test_chat")
				self.assertEqual(chats[0]["model"], "gpt-5.1")
				self.assertEqual(chats[0]["message_count"], 2)
		finally:
			gptcli.CONVERSATIONS_DIR = original_dir
	
	def test_get_available_chats_sorted(self):
		"""Test that chats are sorted by name."""
		# Create multiple conversation files
		for name in ["zebra", "alpha", "beta"]:
			chat_file = os.path.join(self.conversations_dir, f"{name}.json")
			with open(chat_file, 'w') as f:
				json.dump([], f)
		
		original_dir = gptcli.CONVERSATIONS_DIR
		try:
			gptcli.CONVERSATIONS_DIR = self.conversations_dir
			with patch.object(gptcli, 'load_chat_config', return_value={}), \
				 patch.object(gptcli, 'load_conversation', return_value=[]), \
				 patch.object(gptcli, 'DEFAULT_MODEL', "gpt-5.1"):
				chats = get_available_chats()
				self.assertEqual(len(chats), 3)
				self.assertEqual(chats[0]["name"], "alpha")
				self.assertEqual(chats[1]["name"], "beta")
				self.assertEqual(chats[2]["name"], "zebra")
		finally:
			gptcli.CONVERSATIONS_DIR = original_dir
	
	def test_format_chat_entry_short_name(self):
		"""Test formatting chat entry with short name."""
		chat = {
			"name": "test",
			"model": "gpt-5.1",
			"message_count": 10
		}
		formatted = format_chat_entry(chat)
		self.assertIn("test", formatted)
		self.assertIn("gpt-5.1", formatted)
		self.assertIn("10", formatted)
	
	def test_format_chat_entry_long_name(self):
		"""Test formatting chat entry with long name (truncated)."""
		chat = {
			"name": "very_long_chat_name_that_exceeds_limit",
			"model": "gpt-5.1",
			"message_count": 10
		}
		formatted = format_chat_entry(chat)
		# Should be truncated to 21 chars + "..."
		self.assertIn("...", formatted)
		self.assertNotIn("very_long_chat_name_that_exceeds_limit", formatted)
	
	def test_format_chat_entry_exact_length(self):
		"""Test formatting chat entry with name at exact truncation length."""
		chat = {
			"name": "a" * 24,  # Exactly 24 characters
			"model": "gpt-5.1",
			"message_count": 10
		}
		formatted = format_chat_entry(chat)
		# Should not be truncated
		self.assertNotIn("...", formatted)
		self.assertIn("a" * 24, formatted)


if __name__ == '__main__':
	unittest.main()

