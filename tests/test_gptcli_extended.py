"""
Extended tests for gptcli.py - edge cases and error handling.
"""
import importlib
import json
import os
import shutil
import sys
import tempfile
import types
import unittest
from unittest.mock import patch, mock_open

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

gptcli = importlib.import_module("gptcli")


class GptCliExtendedTests(unittest.TestCase):
    """Extended tests for gptcli.py covering edge cases and error handling."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        gptcli.CONVERSATIONS_DIR = os.path.join(self.temp_dir, "conversations")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    # Tests for calculate_cost()
    def test_calculate_cost_model_not_in_pricing(self):
        """Test calculate_cost returns None for model not in pricing."""
        cost = gptcli.calculate_cost("unknown-model", input_tokens=1000, output_tokens=2000)
        self.assertIsNone(cost)

    def test_calculate_cost_zero_tokens(self):
        """Test calculate_cost with zero tokens."""
        cost = gptcli.calculate_cost("gpt-5.1", input_tokens=0, output_tokens=0)
        expected = 0.0
        self.assertAlmostEqual(cost, expected)

    def test_calculate_cost_large_tokens(self):
        """Test calculate_cost with very large token values."""
        cost = gptcli.calculate_cost("gpt-5.1", input_tokens=1_000_000, output_tokens=2_000_000)
        expected = (1_000_000 / 1_000_000) * 2.50 + (2_000_000 / 1_000_000) * 10.00
        self.assertAlmostEqual(cost, expected)

    # Tests for load_conversation() and save_conversation()
    def test_load_conversation_empty_file(self):
        """Test load_conversation with empty file."""
        chat_name = "empty_chat"
        chat_path = gptcli.get_conversation_path(chat_name)
        os.makedirs(os.path.dirname(chat_path), exist_ok=True)
        with open(chat_path, 'w') as f:
            f.write("[]")
        loaded = gptcli.load_conversation(chat_name)
        self.assertEqual(loaded, [])

    def test_load_conversation_invalid_format_string(self):
        """Test load_conversation with invalid format (string instead of list)."""
        chat_name = "invalid_chat"
        chat_path = gptcli.get_conversation_path(chat_name)
        os.makedirs(os.path.dirname(chat_path), exist_ok=True)
        with open(chat_path, 'w') as f:
            f.write('"invalid string"')
        loaded = gptcli.load_conversation(chat_name)
        self.assertEqual(loaded, [])

    def test_load_conversation_invalid_json(self):
        """Test load_conversation with corrupted JSON."""
        chat_name = "corrupted_chat"
        chat_path = gptcli.get_conversation_path(chat_name)
        os.makedirs(os.path.dirname(chat_path), exist_ok=True)
        with open(chat_path, 'w') as f:
            f.write('{"invalid": json}')
        loaded = gptcli.load_conversation(chat_name)
        self.assertEqual(loaded, [])

    def test_load_conversation_missing_file(self):
        """Test load_conversation with missing file."""
        loaded = gptcli.load_conversation("nonexistent_chat")
        self.assertEqual(loaded, [])

    def test_load_conversation_missing_fields(self):
        """Test load_conversation with messages missing fields."""
        chat_name = "incomplete_chat"
        messages = [
            {"role": "user"},  # Missing content
            {"content": "test"},  # Missing role
        ]
        gptcli.save_conversation(chat_name, messages)
        loaded = gptcli.load_conversation(chat_name)
        self.assertEqual(len(loaded), 2)
        self.assertNotIn("content", loaded[0])
        self.assertNotIn("role", loaded[1])

    def test_save_conversation_large_conversation(self):
        """Test save_conversation with very large conversation."""
        chat_name = "large_chat"
        messages = [{"role": "user", "content": f"Message {i}"} for i in range(1000)]
        gptcli.save_conversation(chat_name, messages)
        loaded = gptcli.load_conversation(chat_name)
        self.assertEqual(len(loaded), 1000)

    # Tests for load_statistics() and save_statistics()
    def test_load_statistics_missing_file(self):
        """Test load_statistics with missing file returns defaults."""
        stats = gptcli.load_statistics("nonexistent_chat")
        self.assertEqual(stats["total_input_tokens"], 0)
        self.assertEqual(stats["total_output_tokens"], 0)
        self.assertEqual(stats["total_tokens"], 0)
        self.assertEqual(stats["total_cost"], 0.0)
        self.assertEqual(stats["total_time"], 0.0)
        self.assertEqual(stats["request_count"], 0)

    def test_load_statistics_corrupted_file(self):
        """Test load_statistics with corrupted JSON returns defaults."""
        chat_name = "corrupted_stats"
        stats_path = gptcli.get_stats_path(chat_name)
        os.makedirs(os.path.dirname(stats_path), exist_ok=True)
        with open(stats_path, 'w') as f:
            f.write('{"invalid": json}')
        stats = gptcli.load_statistics(chat_name)
        self.assertEqual(stats["total_input_tokens"], 0)
        self.assertEqual(stats["request_count"], 0)

    def test_load_statistics_missing_fields(self):
        """Test load_statistics with missing fields uses defaults."""
        chat_name = "incomplete_stats"
        stats_path = gptcli.get_stats_path(chat_name)
        os.makedirs(os.path.dirname(stats_path), exist_ok=True)
        with open(stats_path, 'w') as f:
            json.dump({"total_input_tokens": 100}, f)
        stats = gptcli.load_statistics(chat_name)
        self.assertEqual(stats["total_input_tokens"], 100)
        self.assertEqual(stats["total_output_tokens"], 0)  # Default
        self.assertEqual(stats["request_count"], 0)  # Default

    # Tests for update_statistics()
    def test_update_statistics_with_none_chat_name(self):
        """Test update_statistics doesn't save when chat_name is None."""
        original_dir = gptcli.CONVERSATIONS_DIR
        try:
            gptcli.CONVERSATIONS_DIR = self.temp_dir
            gptcli.update_statistics(None, 100, 200, 300, 0.5, 1.0)
            # Should not create stats file
            stats_path = gptcli.get_stats_path("")
            self.assertFalse(os.path.exists(stats_path))
        finally:
            gptcli.CONVERSATIONS_DIR = original_dir

    def test_update_statistics_with_none_cost(self):
        """Test update_statistics handles None cost correctly."""
        chat_name = "none_cost_chat"
        gptcli.update_statistics(chat_name, 100, 200, 300, None, 1.0)
        stats = gptcli.load_statistics(chat_name)
        self.assertEqual(stats["total_input_tokens"], 100)
        self.assertEqual(stats["total_cost"], 0.0)  # Should not add None

    # Tests for path helpers
    def test_get_conversation_path_creates_directory(self):
        """Test get_conversation_path creates directory if it doesn't exist."""
        chat_name = "test_chat"
        path = gptcli.get_conversation_path(chat_name)
        self.assertTrue(os.path.exists(os.path.dirname(path)))

    def test_get_stats_path_creates_directory(self):
        """Test get_stats_path creates statistics directory if it doesn't exist."""
        chat_name = "test_chat"
        path = gptcli.get_stats_path(chat_name)
        self.assertTrue(os.path.exists(os.path.dirname(path)))

    def test_get_chat_config_path_creates_directory(self):
        """Test get_chat_config_path creates directory if it doesn't exist."""
        chat_name = "test_chat"
        path = gptcli.get_chat_config_path(chat_name)
        self.assertTrue(os.path.exists(os.path.dirname(path)))

    # Tests for load_chat_config() and save_chat_config()
    def test_load_chat_config_invalid_json(self):
        """Test load_chat_config with corrupted JSON returns empty dict."""
        chat_name = "corrupted_config"
        config_path = gptcli.get_chat_config_path(chat_name)
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            f.write('{"invalid": json}')
        config = gptcli.load_chat_config(chat_name)
        self.assertEqual(config, {})

    def test_load_chat_config_not_dict(self):
        """Test load_chat_config with non-dict JSON returns empty dict."""
        chat_name = "non_dict_config"
        config_path = gptcli.get_chat_config_path(chat_name)
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            f.write('["not", "a", "dict"]')
        config = gptcli.load_chat_config(chat_name)
        self.assertEqual(config, {})

    # Tests for load_config()
    def test_load_config_missing_file(self):
        """Test load_config returns defaults when file doesn't exist."""
        original_path = gptcli.CONFIG_PATH
        try:
            gptcli.CONFIG_PATH = os.path.join(self.temp_dir, "nonexistent_config.json")
            config = gptcli.load_config()
            self.assertEqual(config["default_model"], "gpt-5.1")
            self.assertIn("system_prompts", config)
        finally:
            gptcli.CONFIG_PATH = original_path

    def test_load_config_corrupted_json(self):
        """Test load_config returns defaults when file is corrupted."""
        original_path = gptcli.CONFIG_PATH
        try:
            config_path = os.path.join(self.temp_dir, "corrupted_config.json")
            with open(config_path, 'w') as f:
                f.write('{"invalid": json}')
            gptcli.CONFIG_PATH = config_path
            config = gptcli.load_config()
            self.assertEqual(config["default_model"], "gpt-5.1")
        finally:
            gptcli.CONFIG_PATH = original_path

    def test_load_config_partial_merge(self):
        """Test load_config merges partial config with defaults."""
        original_path = gptcli.CONFIG_PATH
        try:
            config_path = os.path.join(self.temp_dir, "partial_config.json")
            with open(config_path, 'w') as f:
                json.dump({"default_model": "gpt-4"}, f)
            gptcli.CONFIG_PATH = config_path
            config = gptcli.load_config()
            self.assertEqual(config["default_model"], "gpt-4")
            self.assertIn("system_prompts", config)  # Should still have defaults
            self.assertIn("default", config["system_prompts"])
        finally:
            gptcli.CONFIG_PATH = original_path


if __name__ == "__main__":
    unittest.main()

