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


if __name__ == "__main__":
    unittest.main()

