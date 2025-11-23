#!/usr/bin/env python3
"""
Textual-based UI for GPT CLI chat application.
"""

import os
import json
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, Input, ListView, ListItem, Label
from textual.message import Message
from textual.binding import Binding

# Import functions from gptcli
import gptcli


def get_available_chats():
	"""Get list of available chats with metadata."""
	if not os.path.exists(gptcli.CONVERSATIONS_DIR):
		return []
	chats = []
	for entry in os.listdir(gptcli.CONVERSATIONS_DIR):
		full_path = os.path.join(gptcli.CONVERSATIONS_DIR, entry)
		if os.path.isdir(full_path):
			continue
		if entry.endswith(".config.json"):
			continue
		if entry.endswith(".json"):
			chats.append(entry[:-5])
	metadata = []
	for chat in chats:
		config = gptcli.load_chat_config(chat)
		model = config.get("model", gptcli.DEFAULT_MODEL)
		conversation = gptcli.load_conversation(chat)
		metadata.append({
			"name": chat,
			"model": model,
			"message_count": len(conversation)
		})
	return sorted(metadata, key=lambda item: item["name"])


def format_chat_entry(chat):
	"""Format chat entry for display in list."""
	name = chat["name"] if len(chat["name"]) <= 24 else chat["name"][:21] + "..."
	model = chat["model"]
	return f"{name:<24} | {model:<16} | {chat['message_count']:>5} msgs"


class ChatListItem(ListItem):
	"""List item for a chat."""
	
	def __init__(self, chat_data, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.chat_data = chat_data
	
	def compose(self):
		yield Label(format_chat_entry(self.chat_data))


class ChatListPanel(Container):
	"""Left panel showing list of available chats."""
	
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.border_title = "Chats"
		self.chat_list_view = None
	
	def compose(self) -> ComposeResult:
		self.chat_list_view = ListView(id="chat-list")
		yield self.chat_list_view
	
	def on_mount(self) -> None:
		"""Load chats when panel is mounted."""
		self.load_chats()
	
	def load_chats(self) -> None:
		"""Load and display available chats."""
		chats = get_available_chats()
		self.chat_list_view.clear()
		for chat in chats:
			self.chat_list_view.append(ChatListItem(chat))
	
	def get_selected_chat(self):
		"""Get currently selected chat data."""
		if self.chat_list_view.highlighted_child is None:
			return None
		item = self.chat_list_view.highlighted_child
		if isinstance(item, ChatListItem):
			return item.chat_data
		return None


class ConversationPanel(Static):
	"""Top right panel showing conversation history."""
	
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.border_title = "Conversation"
	
	def compose(self) -> ComposeResult:
		yield Static("Conversation history will go here", classes="conversation-content")


class InputPanel(Container):
	"""Bottom right panel for user input."""
	
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.border_title = "Input"
	
	def compose(self) -> ComposeResult:
		yield Input(placeholder="Type your message here...", id="message-input")


class GptCliApp(App):
	"""Main Textual application for GPT CLI."""
	
	CSS = """
		Screen {
			background: $surface;
		}
		
		#chat-list-panel {
			width: 25%;
			border: solid $primary;
			background: $panel;
		}
		
		#chat-list {
			width: 100%;
			height: 100%;
		}
		
		#chat-list:focus {
			border: solid $accent;
		}
		
		#right-panel {
			width: 1fr;
		}
		
		#conversation-panel {
			height: 75%;
			border: solid $primary;
			background: $surface;
		}
		
		#input-panel {
			height: 25%;
			border: solid $primary;
			background: $panel;
		}
		
		#message-input {
			width: 100%;
			margin: 1;
		}
		
		.chat-list-content,
		.conversation-content {
			width: 100%;
			height: 100%;
			padding: 1;
		}
	"""
	
	BINDINGS = [
		("q", "quit", "Quit"),
		("ctrl+c", "quit", "Quit"),
		("escape", "quit", "Quit"),
		("r", "refresh_chats", "Refresh chats"),
	]
	
	def compose(self) -> ComposeResult:
		"""Create child widgets for the app."""
		with Horizontal():
			yield ChatListPanel(id="chat-list-panel")
			with Vertical(id="right-panel"):
				yield ConversationPanel(id="conversation-panel")
				yield InputPanel(id="input-panel")
	
	def action_quit(self) -> None:
		"""Quit the application."""
		self.exit()
	
	def action_refresh_chats(self) -> None:
		"""Refresh the chat list."""
		chat_list_panel = self.query_one("#chat-list-panel", ChatListPanel)
		chat_list_panel.load_chats()
	
	def on_mount(self) -> None:
		"""Focus on chat list when app starts."""
		chat_list = self.query_one("#chat-list")
		chat_list.focus()


def main():
	"""Main entry point for the UI application."""
	app = GptCliApp()
	app.run()


if __name__ == "__main__":
	main()

