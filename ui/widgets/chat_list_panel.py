from typing import Optional
import os

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import ListView, ListItem, Label

import gptcli
from ..utils import format_chat_entry, get_available_chats
from .conversation_panel import ConversationPanel
from .chat_details_panel import ChatDetailsPanel
from .new_chat_modal import NewChatModal
from .delete_chat_modal import DeleteChatModal
from .edit_system_prompt_modal import EditSystemPromptModal


class ChatListItem(ListItem):
	"""List item for a chat."""
	
	def __init__(self, chat_data, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.chat_data = chat_data
	
	def compose(self) -> ComposeResult:
		yield Label(format_chat_entry(self.chat_data))


class ChatListPanel(Container):
	"""Left panel showing list of available chats."""
	
	BINDINGS = [
		Binding("n", "new_chat", "New chat"),
		Binding("d", "delete_chat", "Delete chat"),
		Binding("e", "edit_chat", "Edit system prompt"),
	]
	
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.border_title = "Chats"
		self.chat_list_view = None
		self._last_highlighted = None
	
	def compose(self) -> ComposeResult:
		self.chat_list_view = ListView(id="chat-list")
		yield self.chat_list_view
	
	def on_mount(self) -> None:
		"""Load chats when panel is mounted."""
		self.load_chats()
		self.set_interval(0.1, self._check_selection_change)
	
	def _check_selection_change(self) -> None:
		"""Check if selection changed and update details and conversation."""
		current = self.chat_list_view.highlighted_child
		if current != self._last_highlighted:
			self._last_highlighted = current
			self.update_details_on_selection()
			app = self.app
			if app:
				conversation_panel = app.query_one("#conversation-panel", ConversationPanel)
				chat_data = self.get_selected_chat()
				if chat_data:
					conversation_panel.load_conversation(chat_data["name"])
				else:
					conversation_panel.load_conversation(None)
	
	def load_chats(self, preserve_selection: bool = True) -> None:
		"""Load and display available chats."""
		selected_chat_name: Optional[str] = None
		if preserve_selection:
			chat_data = self.get_selected_chat()
			if chat_data:
				selected_chat_name = chat_data["name"]
		
		chats = get_available_chats()
		self.chat_list_view.clear()
		for chat in chats:
			self.chat_list_view.append(ChatListItem(chat))
		
		if selected_chat_name and preserve_selection:
			self._restore_selection(selected_chat_name)
	
	def _restore_selection(self, chat_name: str) -> None:
		"""Restore selection after loading chats."""
		for i, item in enumerate(self.chat_list_view.children):
			if isinstance(item, ChatListItem) and item.chat_data["name"] == chat_name:
				self.chat_list_view.index = i
				self.update_details_on_selection()
				app = self.app
				if app:
					conversation_panel = app.query_one("#conversation-panel", ConversationPanel)
					conversation_panel.load_conversation(chat_name)
				break
	
	def get_selected_chat(self):
		"""Get currently selected chat data."""
		if self.chat_list_view.highlighted_child is None:
			return None
		item = self.chat_list_view.highlighted_child
		if isinstance(item, ChatListItem):
			return item.chat_data
		return None
	
	def update_details_on_selection(self) -> None:
		"""Update details panel when selection changes."""
		app = self.app
		if app:
			details_panel = app.query_one("#chat-details-panel", ChatDetailsPanel)
			chat_data = self.get_selected_chat()
			details_panel.update_chat_details(chat_data)
	
	def on_list_view_selected(self, event) -> None:
		"""Handle chat selection (Enter key)."""
		chat_data = self.get_selected_chat()
		if chat_data:
			app = self.app
			if app:
				conversation_panel = app.query_one("#conversation-panel", ConversationPanel)
				conversation_panel.load_conversation(chat_data["name"])
	
	def on_list_view_highlighted(self, event) -> None:
		"""Handle chat selection change."""
		app = self.app
		if app:
			details_panel = app.query_one("#chat-details-panel", ChatDetailsPanel)
			chat_data = self.get_selected_chat()
			details_panel.update_chat_details(chat_data)
			
	def action_new_chat(self) -> None:
		app = self.app
		if not app:
			return
		
		def handle_result(result) -> None:
			"""Handle result from modal - create new chat and set it as active."""
			if not result:
				return
			
			if isinstance(result, str):
				chat_name = result.strip()
				system_prompt = ""
			else:
				chat_name = (result.get("name", "") if isinstance(result, dict) else "").strip()
				system_prompt = (result.get("system_prompt", "") if isinstance(result, dict) else "").strip()
			
			if not chat_name:
				app.bell()
				return
			
			chat_path = gptcli.get_conversation_path(chat_name)
			if os.path.exists(chat_path):
				app.bell()
				self.load_chats()
				self._restore_selection(chat_name)
				return
			
			gptcli.save_conversation(chat_name, [])
			if system_prompt:
				gptcli.save_system_prompt(chat_name, system_prompt)
			self.load_chats(preserve_selection=False)
			self._restore_selection(chat_name)
			
			def focus_input():
				input_panel = app.query_one("#input-panel")
				if hasattr(input_panel, "message_input") and input_panel.message_input:
					input_panel.message_input.focus()
			
			app.call_after_refresh(focus_input)
		
		app.push_screen(NewChatModal(), handle_result)
	
	def action_delete_chat(self) -> None:
		"""Delete selected chat."""
		chat_data = self.get_selected_chat()
		if not chat_data:
			app = self.app
			if app:
				app.bell()
			return
		
		chat_name = chat_data["name"]
		app = self.app
		if not app:
			return
		
		def handle_result(confirmed: Optional[bool]) -> None:
			"""Handle result from delete confirmation modal."""
			if not confirmed:
				return
			
			chat_path = gptcli.get_conversation_path(chat_name)
			config_path = gptcli.get_chat_config_path(chat_name)
			stats_path = gptcli.get_stats_path(chat_name)
			system_prompt_path = gptcli.get_system_prompt_path(chat_name)
			
			if os.path.exists(chat_path):
				os.remove(chat_path)
			if os.path.exists(config_path):
				os.remove(config_path)
			if os.path.exists(stats_path):
				os.remove(stats_path)
			if os.path.exists(system_prompt_path):
				os.remove(system_prompt_path)
			
			self.load_chats(preserve_selection=False)
			
			conversation_panel = app.query_one("#conversation-panel", ConversationPanel)
			conversation_panel.load_conversation(None)
			
			details_panel = app.query_one("#chat-details-panel", ChatDetailsPanel)
			details_panel.update_chat_details(None)
		
		app.push_screen(DeleteChatModal(chat_name), handle_result)

	def action_edit_chat(self) -> None:
		"""Edit system prompt for selected chat."""
		chat_data = self.get_selected_chat()
		if not chat_data:
			app = self.app
			if app:
				app.bell()
			return
		
		chat_name = chat_data["name"]
		app = self.app
		if not app:
			return
		
		current_prompt = gptcli.load_system_prompt(chat_name)
		
		def handle_result(new_prompt):
			if new_prompt is None:
				return
			gptcli.save_system_prompt(chat_name, new_prompt)
			details_panel = app.query_one("#chat-details-panel", ChatDetailsPanel)
			details_panel.update_chat_details(chat_data)
		
		app.push_screen(EditSystemPromptModal(chat_name, current_prompt), handle_result)

