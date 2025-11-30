"""
Tests for widget logic (business logic only, mocking Textual components).
"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import Mock, MagicMock, patch

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


rich_text = types.ModuleType("rich.text")


class DummyText(str):
    def __new__(cls, text, *args, **kwargs):
        return str.__new__(cls, text)


rich_console.Console = DummyConsole
rich_markdown.Markdown = DummyMarkdown
rich_progress.Progress = DummyProgress
rich_progress.SpinnerColumn = lambda *args, **kwargs: None
rich_progress.TextColumn = lambda *args, **kwargs: None
rich_progress.TimeElapsedColumn = lambda *args, **kwargs: None
rich_live.Live = DummyLive
rich_text.Text = DummyText

sys.modules["rich"] = rich_module
sys.modules["rich.console"] = rich_console
sys.modules["rich.markdown"] = rich_markdown
sys.modules["rich.progress"] = rich_progress
sys.modules["rich.live"] = rich_live
sys.modules["rich.text"] = rich_text

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

# Stub Textual
textual_module = types.ModuleType("textual")
textual_app = types.ModuleType("textual.app")
textual_containers = types.ModuleType("textual.containers")
textual_widgets = types.ModuleType("textual.widgets")
textual_binding = types.ModuleType("textual.binding")
textual_message = types.ModuleType("textual.message")
textual_screen = types.ModuleType("textual.screen")
textual_events = types.ModuleType("textual.events")

# Create dummy classes
class DummyApp:
    pass


class DummyContainer:
    def __init__(self, *args, **kwargs):
        self.mount = Mock()
        self.is_attached = True
        self.styles = DummyStyles()


class DummyStyles:
    def __init__(self):
        self.border_left = None


class DummyWidget:
    def __init__(self, *args, **kwargs):
        self.styles = DummyStyles()
        self._args = args
        self._kwargs = kwargs
    
    def __str__(self):
        # Return first string argument if available, otherwise default
        if self._args and isinstance(self._args[0], str):
            return self._args[0]
        return f"DummyWidget({self._args[0] if self._args else ''})"


class DummyBinding:
    def __init__(self, *args, **kwargs):
        pass


class DummyMessage:
    pass


class DummyModalScreen:
    pass


class DummyKey:
    pass


class DummyEvents:
    Key = DummyKey


# ComposeResult is a type alias, use a simple type
ComposeResult = type(None)

textual_app.App = DummyApp
textual_app.ComposeResult = ComposeResult
textual_containers.Container = DummyContainer
textual_containers.ScrollableContainer = DummyContainer
textual_containers.Vertical = DummyContainer
textual_containers.Horizontal = DummyContainer
textual_containers.Center = DummyContainer
textual_widgets.ListView = DummyWidget
textual_widgets.ListItem = DummyWidget
textual_widgets.Static = DummyWidget
textual_widgets.Markdown = DummyWidget
textual_widgets.Label = DummyWidget
textual_widgets.Button = DummyWidget
textual_widgets.Input = DummyWidget
textual_widgets.TextArea = DummyWidget
textual_binding.Binding = DummyBinding
textual_message.Message = DummyMessage
textual_screen.ModalScreen = DummyModalScreen
textual_events.events = DummyEvents
textual_events.Key = DummyKey

sys.modules["textual"] = textual_module
sys.modules["textual.app"] = textual_app
sys.modules["textual.containers"] = textual_containers
sys.modules["textual.widgets"] = textual_widgets
sys.modules["textual.binding"] = textual_binding
sys.modules["textual.message"] = textual_message
sys.modules["textual.screen"] = textual_screen
sys.modules["textual.events"] = textual_events

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


class TestChatListPanelLogic(unittest.TestCase):
    """Tests for ChatListPanel business logic."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.conversations_dir = os.path.join(self.test_dir, "conversations")
        os.makedirs(self.conversations_dir)
        gptcli.CONVERSATIONS_DIR = self.conversations_dir

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)

    def _import_widget(self, widget_name, module_path):
        """Helper to import widget directly without going through ui/__init__.py"""
        spec = importlib.util.spec_from_file_location(
            f"ui.widgets.{widget_name}",
            os.path.join(os.path.dirname(__file__), '..', 'ui', 'widgets', module_path)
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_get_selected_chat_returns_none_when_nothing_selected(self):
        """Test get_selected_chat returns None when nothing is selected."""
        # Import after stubs are set up
        chat_list_panel_module = self._import_widget("chat_list_panel", "chat_list_panel.py")
        ChatListPanel = chat_list_panel_module.ChatListPanel

        panel = ChatListPanel()
        panel.chat_list_view = Mock()
        panel.chat_list_view.highlighted_child = None

        result = panel.get_selected_chat()
        self.assertIsNone(result)

    def test_get_selected_chat_returns_chat_data(self):
        """Test get_selected_chat returns correct chat_data."""
        chat_list_panel_module = self._import_widget("chat_list_panel", "chat_list_panel.py")
        ChatListPanel = chat_list_panel_module.ChatListPanel
        ChatListItem = chat_list_panel_module.ChatListItem

        panel = ChatListPanel()
        panel.chat_list_view = Mock()
        
        chat_data = {"name": "test_chat", "model": "gpt-5.1", "message_count": 5}
        item = ChatListItem(chat_data)
        panel.chat_list_view.highlighted_child = item

        result = panel.get_selected_chat()
        self.assertEqual(result, chat_data)

    def test_load_chats_preserves_selection(self):
        """Test load_chats preserves selection when preserve_selection=True."""
        chat_list_panel_module = self._import_widget("chat_list_panel", "chat_list_panel.py")
        ChatListPanel = chat_list_panel_module.ChatListPanel

        # Create test chat
        chat_name = "test_chat"
        chat_file = os.path.join(self.conversations_dir, f"{chat_name}.json")
        with open(chat_file, 'w') as f:
            json.dump([{"role": "user", "content": "test"}], f)

        panel = ChatListPanel()
        panel.chat_list_view = Mock()
        panel.chat_list_view.clear = Mock()
        panel.chat_list_view.append = Mock()
        panel.chat_list_view.children = []
        panel._restore_selection = Mock()

        # Mock get_selected_chat to return a chat
        panel.get_selected_chat = Mock(return_value={"name": chat_name})

        panel.load_chats(preserve_selection=True)

        # Should call _restore_selection
        panel._restore_selection.assert_called_once_with(chat_name)

    def test_load_chats_does_not_preserve_selection(self):
        """Test load_chats doesn't preserve selection when preserve_selection=False."""
        chat_list_panel_module = self._import_widget("chat_list_panel", "chat_list_panel.py")
        ChatListPanel = chat_list_panel_module.ChatListPanel

        panel = ChatListPanel()
        panel.chat_list_view = Mock()
        panel.chat_list_view.clear = Mock()
        panel.chat_list_view.append = Mock()
        panel.chat_list_view.children = []
        panel._restore_selection = Mock()

        panel.load_chats(preserve_selection=False)

        # Should not call _restore_selection
        panel._restore_selection.assert_not_called()


class TestConversationPanelLogic(unittest.TestCase):
    """Tests for ConversationPanel business logic."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.conversations_dir = os.path.join(self.test_dir, "conversations")
        os.makedirs(self.conversations_dir)
        gptcli.CONVERSATIONS_DIR = self.conversations_dir

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)

    def _import_widget(self, widget_name, module_path):
        """Helper to import widget directly without going through ui/__init__.py"""
        spec = importlib.util.spec_from_file_location(
            f"ui.widgets.{widget_name}",
            os.path.join(os.path.dirname(__file__), '..', 'ui', 'widgets', module_path)
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_load_conversation_handles_none(self):
        """Test load_conversation handles None (no chat selected)."""
        conversation_panel_module = self._import_widget("conversation_panel", "conversation_panel.py")
        ConversationPanel = conversation_panel_module.ConversationPanel

        panel = ConversationPanel()
        panel.conversation_container = Mock()
        panel.conversation_container.remove_children = Mock()
        panel.conversation_container.mount = Mock()

        panel.load_conversation(None)

        panel.conversation_container.remove_children.assert_called_once()
        panel.conversation_container.mount.assert_called_once()
        # Check that it mounted empty message
        call_args = panel.conversation_container.mount.call_args[0][0]
        self.assertIn("Select a chat", str(call_args))

    def test_load_conversation_handles_empty_conversation(self):
        """Test load_conversation handles empty conversation."""
        chat_name = "empty_chat"
        chat_file = os.path.join(self.conversations_dir, f"{chat_name}.json")
        with open(chat_file, 'w') as f:
            json.dump([], f)

        conversation_panel_module = self._import_widget("conversation_panel", "conversation_panel.py")
        ConversationPanel = conversation_panel_module.ConversationPanel

        panel = ConversationPanel()
        panel.conversation_container = Mock()
        panel.conversation_container.remove_children = Mock()
        panel.conversation_container.mount = Mock()
        panel.post_message = Mock()

        panel.load_conversation(chat_name)

        panel.conversation_container.remove_children.assert_called_once()
        # Should mount empty message
        panel.conversation_container.mount.assert_called_once()

    def test_load_conversation_formats_user_messages(self):
        """Test load_conversation formats user messages correctly."""
        chat_name = "test_chat"
        chat_file = os.path.join(self.conversations_dir, f"{chat_name}.json")
        messages = [
            {"role": "user", "content": "Hello"}
        ]
        with open(chat_file, 'w') as f:
            json.dump(messages, f)

        conversation_panel_module = self._import_widget("conversation_panel", "conversation_panel.py")
        ConversationPanel = conversation_panel_module.ConversationPanel

        panel = ConversationPanel()
        panel.conversation_container = Mock()
        panel.conversation_container.remove_children = Mock()
        panel.conversation_container.mount = Mock()
        panel.post_message = Mock()

        panel.load_conversation(chat_name)

        # Should mount message_container (which contains header and content) for user message
        self.assertEqual(panel.conversation_container.mount.call_count, 1)

    def test_load_conversation_formats_assistant_messages(self):
        """Test load_conversation formats assistant messages correctly."""
        chat_name = "test_chat"
        chat_file = os.path.join(self.conversations_dir, f"{chat_name}.json")
        messages = [
            {"role": "assistant", "content": "Hi there!", "model": "gpt-5.1"}
        ]
        with open(chat_file, 'w') as f:
            json.dump(messages, f)

        conversation_panel_module = self._import_widget("conversation_panel", "conversation_panel.py")
        ConversationPanel = conversation_panel_module.ConversationPanel

        panel = ConversationPanel()
        panel.conversation_container = Mock()
        panel.conversation_container.remove_children = Mock()
        panel.conversation_container.mount = Mock()
        panel.post_message = Mock()

        panel.load_conversation(chat_name)

        # Should mount message_container (which contains header and content) for assistant message
        self.assertEqual(panel.conversation_container.mount.call_count, 1)

    def test_load_conversation_handles_missing_model(self):
        """Test load_conversation handles messages without model (gets from config)."""
        chat_name = "test_chat"
        chat_file = os.path.join(self.conversations_dir, f"{chat_name}.json")
        messages = [
            {"role": "assistant", "content": "Hi there!"}  # No model
        ]
        with open(chat_file, 'w') as f:
            json.dump(messages, f)

        # Create config with model
        config_file = os.path.join(self.conversations_dir, f"{chat_name}.config.json")
        with open(config_file, 'w') as f:
            json.dump({"model": "gpt-4"}, f)

        conversation_panel_module = self._import_widget("conversation_panel", "conversation_panel.py")
        ConversationPanel = conversation_panel_module.ConversationPanel

        panel = ConversationPanel()
        panel.conversation_container = Mock()
        panel.conversation_container.remove_children = Mock()
        panel.conversation_container.mount = Mock()
        panel.post_message = Mock()

        panel.load_conversation(chat_name)

        # Should still mount message_container (which contains header and content)
        self.assertEqual(panel.conversation_container.mount.call_count, 1)


class TestChatDetailsPanelLogic(unittest.TestCase):
    """Tests for ChatDetailsPanel business logic."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.conversations_dir = os.path.join(self.test_dir, "conversations")
        os.makedirs(self.conversations_dir)
        gptcli.CONVERSATIONS_DIR = self.conversations_dir

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)

    def _import_widget(self, widget_name, module_path):
        """Helper to import widget directly without going through ui/__init__.py"""
        spec = importlib.util.spec_from_file_location(
            f"ui.widgets.{widget_name}",
            os.path.join(os.path.dirname(__file__), '..', 'ui', 'widgets', module_path)
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_update_chat_details_handles_none(self):
        """Test update_chat_details handles None."""
        chat_details_panel_module = self._import_widget("chat_details_panel", "chat_details_panel.py")
        ChatDetailsPanel = chat_details_panel_module.ChatDetailsPanel

        panel = ChatDetailsPanel()
        panel.details_content = Mock()
        panel.details_content.update = Mock()

        panel.update_chat_details(None)

        panel.details_content.update.assert_called_once()
        call_args = panel.details_content.update.call_args[0][0]
        self.assertIn("Select a chat", call_args)

    def test_update_chat_details_displays_statistics(self):
        """Test update_chat_details displays statistics correctly."""
        chat_name = "test_chat"
        chat_file = os.path.join(self.conversations_dir, f"{chat_name}.json")
        with open(chat_file, 'w') as f:
            json.dump([{"role": "user", "content": "test"}], f)

        # Create stats
        stats_dir = os.path.join(self.conversations_dir, "statistics")
        os.makedirs(stats_dir, exist_ok=True)
        stats_file = os.path.join(stats_dir, f"{chat_name}.json")
        with open(stats_file, 'w') as f:
            json.dump({
                "total_tokens": 1000,
                "total_input_tokens": 400,
                "total_output_tokens": 600,
                "total_cost": 0.05,
                "total_time": 2.5,
                "request_count": 3
            }, f)

        chat_details_panel_module = self._import_widget("chat_details_panel", "chat_details_panel.py")
        ChatDetailsPanel = chat_details_panel_module.ChatDetailsPanel

        panel = ChatDetailsPanel()
        panel.details_content = Mock()
        panel.details_content.update = Mock()

        chat_data = {"name": chat_name, "model": "gpt-5.1", "message_count": 1}
        panel.update_chat_details(chat_data)

        panel.details_content.update.assert_called_once()
        call_args = panel.details_content.update.call_args[0][0]
        self.assertIn("1,000", call_args)  # Formatted with comma
        self.assertIn("$0.05", call_args)
        self.assertIn("2.50s", call_args)

    def test_update_chat_details_handles_missing_system_prompt(self):
        """Test update_chat_details handles missing system prompt."""
        chat_name = "test_chat"
        chat_file = os.path.join(self.conversations_dir, f"{chat_name}.json")
        with open(chat_file, 'w') as f:
            json.dump([], f)

        chat_details_panel_module = self._import_widget("chat_details_panel", "chat_details_panel.py")
        ChatDetailsPanel = chat_details_panel_module.ChatDetailsPanel

        panel = ChatDetailsPanel()
        panel.details_content = Mock()
        panel.details_content.update = Mock()

        chat_data = {"name": chat_name, "model": "gpt-5.1", "message_count": 0}
        panel.update_chat_details(chat_data)

        call_args = panel.details_content.update.call_args[0][0]
        self.assertIn("(default)", call_args)

    def test_update_chat_details_handles_custom_system_prompt(self):
        """Test update_chat_details handles custom system prompt (long text)."""
        chat_name = "test_chat"
        chat_file = os.path.join(self.conversations_dir, f"{chat_name}.json")
        with open(chat_file, 'w') as f:
            json.dump([], f)

        # Create config with custom system prompt
        config_file = os.path.join(self.conversations_dir, f"{chat_name}.config.json")
        custom_prompt = "This is a very long custom system prompt that should be truncated"
        with open(config_file, 'w') as f:
            json.dump({"system_prompt": custom_prompt}, f)

        chat_details_panel_module = self._import_widget("chat_details_panel", "chat_details_panel.py")
        ChatDetailsPanel = chat_details_panel_module.ChatDetailsPanel

        panel = ChatDetailsPanel()
        panel.details_content = Mock()
        panel.details_content.update = Mock()

        chat_data = {"name": chat_name, "model": "gpt-5.1", "message_count": 0}
        panel.update_chat_details(chat_data)

        call_args = panel.details_content.update.call_args[0][0]
        # Should show preview (first 40 chars + "...")
        self.assertIn(custom_prompt[:40], call_args)
        self.assertIn("...", call_args)


if __name__ == '__main__':
    unittest.main()

