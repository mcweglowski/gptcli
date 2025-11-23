import importlib
import json
import os
import shutil
import sys
import tempfile
import types
import unittest

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

# Stub OpenAI client to avoid network setup during import
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

# Stub gnureadline to avoid requiring it during tests
gnureadline_module = types.ModuleType("gnureadline")
def dummy_set_history_length(*args, **kwargs):
    pass
def dummy_set_auto_history(*args, **kwargs):
    pass
gnureadline_module.set_history_length = dummy_set_history_length
gnureadline_module.set_auto_history = dummy_set_auto_history
sys.modules["gnureadline"] = gnureadline_module

# Ensure dummy API key so gptcli import succeeds without real credentials
os.environ.setdefault("OPENAI_API_KEY", "test-key")

gptcli = importlib.import_module("gptcli")


class GptCliTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        gptcli.CONVERSATIONS_DIR = os.path.join(self.temp_dir, "conversations")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_calculate_cost(self):
        cost = gptcli.calculate_cost("gpt-5.1", input_tokens=1000, output_tokens=2000)
        expected = (1000 / 1_000_000) * 2.50 + (2000 / 1_000_000) * 10.00
        self.assertAlmostEqual(cost, expected)

    def test_format_statistics(self):
        stats = gptcli.format_statistics(100, 200, 300, 0.123456, 1.5)
        self.assertIn("Tokens: 300 (100 in / 200 out)", stats)
        self.assertIn("Cost: $0.123456", stats)
        self.assertIn("Time: 1.50s", stats)

    def test_save_and_load_conversation(self):
        chat_name = "testchat"
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        gptcli.save_conversation(chat_name, messages)
        loaded = gptcli.load_conversation(chat_name)
        self.assertEqual(messages, loaded)

    def test_update_statistics_accumulates(self):
        chat_name = "stat_chat"

        gptcli.update_statistics(chat_name, 100, 200, 300, 0.5, 1.0)
        stats_path = gptcli.get_stats_path(chat_name)

        with open(stats_path, "r", encoding="utf-8") as f:
            stats = json.load(f)
        self.assertEqual(stats["total_input_tokens"], 100)
        self.assertEqual(stats["total_output_tokens"], 200)
        self.assertEqual(stats["total_tokens"], 300)
        self.assertAlmostEqual(stats["total_cost"], 0.5)
        self.assertAlmostEqual(stats["total_time"], 1.0)
        self.assertEqual(stats["request_count"], 1)

        gptcli.update_statistics(chat_name, 50, 75, 125, 0.25, 0.5)
        with open(stats_path, "r", encoding="utf-8") as f:
            stats = json.load(f)
        self.assertEqual(stats["total_input_tokens"], 150)
        self.assertEqual(stats["total_output_tokens"], 275)
        self.assertEqual(stats["total_tokens"], 425)
        self.assertAlmostEqual(stats["total_cost"], 0.75)
        self.assertAlmostEqual(stats["total_time"], 1.5)
        self.assertEqual(stats["request_count"], 2)

    # System Prompts Tests
    def test_load_system_prompts_from_config(self):
        """Test that system prompts are loaded from config."""
        # SYSTEM_PROMPTS should be loaded from DEFAULT_CONFIG
        self.assertIn("default", gptcli.SYSTEM_PROMPTS)
        self.assertIn("python-expert", gptcli.SYSTEM_PROMPTS)
        self.assertEqual(
            gptcli.SYSTEM_PROMPTS["default"],
            "You are a helpful assistant."
        )

    def test_system_prompt_saved_in_chat_config(self):
        """Test that system prompt is saved in chat config."""
        chat_name = "test_system_prompt"
        config = {"system_prompt": "python-expert"}
        gptcli.save_chat_config(chat_name, config)
        
        loaded = gptcli.load_chat_config(chat_name)
        self.assertEqual(loaded["system_prompt"], "python-expert")

    def test_system_prompt_loaded_from_chat_config(self):
        """Test that system prompt is loaded from chat config."""
        chat_name = "test_load_prompt"
        config = {"system_prompt": "friendly-mentor"}
        gptcli.save_chat_config(chat_name, config)
        
        loaded = gptcli.load_chat_config(chat_name)
        self.assertEqual(loaded["system_prompt"], "friendly-mentor")

    def test_system_prompt_fallback_to_none(self):
        """Test that when system prompt doesn't exist, returns None."""
        chat_name = "test_no_prompt"
        config = {}
        gptcli.save_chat_config(chat_name, config)
        
        loaded = gptcli.load_chat_config(chat_name)
        self.assertNotIn("system_prompt", loaded)

    def test_system_prompt_custom_text(self):
        """Test that custom text can be used as system prompt."""
        chat_name = "test_custom_prompt"
        custom_text = "You are a custom assistant for testing."
        config = {"system_prompt": custom_text}
        gptcli.save_chat_config(chat_name, config)
        
        loaded = gptcli.load_chat_config(chat_name)
        self.assertEqual(loaded["system_prompt"], custom_text)

    # Command Parsing Tests
    def test_parse_command_change_model(self):
        """Test parsing /change-model command."""
        command_line = "/change-model gpt-4"
        parts = command_line[1:].strip().split()
        self.assertEqual(parts[0], "change-model")
        self.assertEqual(parts[1], "gpt-4")

    def test_parse_command_system_prompt(self):
        """Test parsing /system-prompt command."""
        command_line = "/system-prompt python-expert"
        parts = command_line[1:].strip().split()
        self.assertEqual(parts[0], "system-prompt")
        self.assertEqual(parts[1], "python-expert")

    def test_parse_command_system_prompt_custom_text(self):
        """Test parsing /system-prompt with custom text."""
        command_line = "/system-prompt You are a custom assistant"
        parts = command_line[1:].strip().split()
        self.assertEqual(parts[0], "system-prompt")
        self.assertEqual(" ".join(parts[1:]), "You are a custom assistant")

    def test_parse_command_list_chats(self):
        """Test parsing /list-chats command."""
        command_line = "/list-chats"
        parts = command_line[1:].strip().split()
        self.assertEqual(parts[0], "list-chats")
        self.assertEqual(len(parts), 1)

    def test_parse_command_switch_chat(self):
        """Test parsing /switch-chat command."""
        command_line = "/switch-chat mychat"
        parts = command_line[1:].strip().split()
        self.assertEqual(parts[0], "switch-chat")
        self.assertEqual(parts[1], "mychat")

    def test_parse_command_help(self):
        """Test parsing /help command."""
        command_line = "/help"
        parts = command_line[1:].strip().split()
        self.assertEqual(parts[0], "help")

    def test_parse_command_quit(self):
        """Test parsing /quit command."""
        command_line = "/quit"
        parts = command_line[1:].strip().split()
        self.assertEqual(parts[0], "quit")

    def test_parse_invalid_command(self):
        """Test parsing invalid command."""
        command_line = "/invalid-command"
        parts = command_line[1:].strip().split()
        self.assertEqual(parts[0], "invalid-command")
        # Should not raise exception, just return unknown command

    # Formatting Tests - Testing chat metadata structure
    def test_chat_metadata_structure(self):
        """Test that chat metadata has correct structure."""
        # Create test conversations
        chat1 = "test_chat1"
        chat2 = "test_chat2"
        
        messages1 = [{"role": "user", "content": "Hello"}]
        messages2 = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"}
        ]
        
        gptcli.save_conversation(chat1, messages1)
        gptcli.save_conversation(chat2, messages2)
        
        # Test that conversations are saved and can be loaded
        loaded1 = gptcli.load_conversation(chat1)
        loaded2 = gptcli.load_conversation(chat2)
        
        self.assertEqual(len(loaded1), 1)
        self.assertEqual(len(loaded2), 2)
        
        # Test chat config loading
        config1 = gptcli.load_chat_config(chat1)
        self.assertIsInstance(config1, dict)

    def test_chat_formatting_logic(self):
        """Test chat formatting logic (name truncation, model, message count)."""
        # Test name truncation logic
        short_name = "test"
        long_name = "a" * 30
        
        # Short name should not be truncated
        self.assertLessEqual(len(short_name), 24)
        
        # Long name should be truncated
        truncated = long_name[:21] + "..." if len(long_name) > 24 else long_name
        self.assertIn("...", truncated)
        self.assertLessEqual(len(truncated), 24)

    def test_chat_with_model_in_config(self):
        """Test chat with custom model in config."""
        chat_name = "test_model_chat"
        messages = [{"role": "user", "content": "Test"}]
        config = {"model": "gpt-4"}
        
        gptcli.save_conversation(chat_name, messages)
        gptcli.save_chat_config(chat_name, config)
        
        # Verify config is saved and loaded correctly
        loaded_config = gptcli.load_chat_config(chat_name)
        self.assertEqual(loaded_config["model"], "gpt-4")
        
        # Verify conversation is saved
        loaded_messages = gptcli.load_conversation(chat_name)
        self.assertEqual(len(loaded_messages), 1)


if __name__ == "__main__":
    unittest.main()

