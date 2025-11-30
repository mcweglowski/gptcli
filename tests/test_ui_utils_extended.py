"""
Extended tests for ui/utils.py - edge cases.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

# Import gptcli first (with stubs from test_gptcli)
import importlib
import types

# Stub required Rich components
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

# Import UI utils
import importlib.util
utils_path = os.path.join(os.path.dirname(__file__), '..', 'ui', 'utils.py')
spec = importlib.util.spec_from_file_location("ui_utils", utils_path)
ui_utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ui_utils)

get_available_chats = ui_utils.get_available_chats
format_chat_entry = ui_utils.format_chat_entry


class TestUIUtilsExtended(unittest.TestCase):
    """Extended tests for UI utility functions - edge cases."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.conversations_dir = os.path.join(self.test_dir, "conversations")
        os.makedirs(self.conversations_dir)

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)

    # Tests for get_available_chats()
    def test_get_available_chats_different_models(self):
        """Test getting chats with different models."""
        # Create multiple chats with different models
        for name, model in [("chat1", "gpt-5.1"), ("chat2", "gpt-4"), ("chat3", "gpt-3.5")]:
            chat_file = os.path.join(self.conversations_dir, f"{name}.json")
            with open(chat_file, 'w') as f:
                json.dump([{"role": "user", "content": "test"}], f)
            config_file = os.path.join(self.conversations_dir, f"{name}.config.json")
            with open(config_file, 'w') as f:
                json.dump({"model": model}, f)

        original_dir = gptcli.CONVERSATIONS_DIR
        try:
            gptcli.CONVERSATIONS_DIR = self.conversations_dir
            chats = get_available_chats()
            self.assertEqual(len(chats), 3)
            models = {chat["model"] for chat in chats}
            self.assertIn("gpt-5.1", models)
            self.assertIn("gpt-4", models)
            self.assertIn("gpt-3.5", models)
        finally:
            gptcli.CONVERSATIONS_DIR = original_dir

    def test_get_available_chats_empty_conversations(self):
        """Test getting chats with empty conversations."""
        chat_file = os.path.join(self.conversations_dir, "empty_chat.json")
        with open(chat_file, 'w') as f:
            json.dump([], f)

        original_dir = gptcli.CONVERSATIONS_DIR
        try:
            gptcli.CONVERSATIONS_DIR = self.conversations_dir
            chats = get_available_chats()
            self.assertEqual(len(chats), 1)
            self.assertEqual(chats[0]["message_count"], 0)
        finally:
            gptcli.CONVERSATIONS_DIR = original_dir

    def test_get_available_chats_very_long_names(self):
        """Test getting chats with very long names."""
        long_name = "a" * 100
        chat_file = os.path.join(self.conversations_dir, f"{long_name}.json")
        with open(chat_file, 'w') as f:
            json.dump([{"role": "user", "content": "test"}], f)

        original_dir = gptcli.CONVERSATIONS_DIR
        try:
            gptcli.CONVERSATIONS_DIR = self.conversations_dir
            chats = get_available_chats()
            self.assertEqual(len(chats), 1)
            self.assertEqual(chats[0]["name"], long_name)
        finally:
            gptcli.CONVERSATIONS_DIR = original_dir

    def test_get_available_chats_missing_config(self):
        """Test getting chats with missing config files."""
        chat_file = os.path.join(self.conversations_dir, "no_config_chat.json")
        with open(chat_file, 'w') as f:
            json.dump([{"role": "user", "content": "test"}], f)
        # Don't create config file

        original_dir = gptcli.CONVERSATIONS_DIR
        try:
            gptcli.CONVERSATIONS_DIR = self.conversations_dir
            with patch.object(gptcli, 'DEFAULT_MODEL', "gpt-5.1"):
                chats = get_available_chats()
                self.assertEqual(len(chats), 1)
                self.assertEqual(chats[0]["model"], "gpt-5.1")  # Should use default
        finally:
            gptcli.CONVERSATIONS_DIR = original_dir

    # Tests for format_chat_entry()
    def test_format_chat_entry_zero_length_name(self):
        """Test formatting chat entry with zero-length name (edge case)."""
        chat = {
            "name": "",
            "model": "gpt-5.1",
            "message_count": 10
        }
        formatted = format_chat_entry(chat)
        self.assertEqual("", formatted)

    def test_format_chat_entry_very_long_name(self):
        """Test formatting chat entry with very long name (>100 chars)."""
        very_long_name = "a" * 150
        chat = {
            "name": very_long_name,
            "model": "gpt-5.1",
            "message_count": 10
        }
        formatted = format_chat_entry(chat)
        # Should return full name without truncation
        self.assertEqual(very_long_name, formatted)

    def test_format_chat_entry_different_message_counts(self):
        """Test formatting chat entry with different message counts (should ignore counts)."""
        test_cases = [0, 1, 100, 1000, 99999]

        for count in test_cases:
            chat = {
                "name": "test",
                "model": "gpt-5.1",
                "message_count": count
            }
            formatted = format_chat_entry(chat)
            # Should return only the name, regardless of message count
            self.assertEqual("test", formatted, f"Failed for count {count}")

    def test_format_chat_entry_exact_24_chars(self):
        """Test formatting chat entry with name exactly 24 characters."""
        exact_name = "a" * 24
        chat = {
            "name": exact_name,
            "model": "gpt-5.1",
            "message_count": 10
        }
        formatted = format_chat_entry(chat)
        # Should return full name
        self.assertEqual(exact_name, formatted)

    def test_format_chat_entry_25_chars(self):
        """Test formatting chat entry with name 25 characters (should not be truncated)."""
        long_name = "a" * 25
        chat = {
            "name": long_name,
            "model": "gpt-5.1",
            "message_count": 10
        }
        formatted = format_chat_entry(chat)
        # Should return full name without truncation
        self.assertEqual(long_name, formatted)


if __name__ == '__main__':
    unittest.main()

