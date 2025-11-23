#!/usr/bin/env python3
"""
Textual-based UI for GPT CLI chat application.
"""

import os
import json
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Static, Input, ListView, ListItem, Label, Markdown
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
		self._last_highlighted = None
	
	def compose(self) -> ComposeResult:
		self.chat_list_view = ListView(id="chat-list")
		yield self.chat_list_view
	
	def on_mount(self) -> None:
		"""Load chats when panel is mounted."""
		self.load_chats()
		# Set up a timer to check for selection changes
		self.set_interval(0.1, self._check_selection_change)
	
	def _check_selection_change(self) -> None:
		"""Check if selection changed and update details and conversation."""
		current = self.chat_list_view.highlighted_child
		if current != self._last_highlighted:
			self._last_highlighted = current
			self.update_details_on_selection()
			# Also update conversation panel
			app = self.app
			if app:
				conversation_panel = app.query_one("#conversation-panel", ConversationPanel)
				chat_data = self.get_selected_chat()
				if chat_data:
					conversation_panel.load_conversation(chat_data["name"])
				else:
					conversation_panel.load_conversation(None)
	
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
		# Get the app instance to update details panel
		app = self.app
		if app:
			details_panel = app.query_one("#chat-details-panel", ChatDetailsPanel)
			chat_data = self.get_selected_chat()
			details_panel.update_chat_details(chat_data)


class ChatDetailsPanel(Container):
	"""Panel showing chat details and statistics."""
	
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.border_title = "Chat Details & Stats"
		self.details_content = None
	
	def compose(self) -> ComposeResult:
		self.details_content = Static("Select a chat to view details", classes="chat-details-content")
		yield self.details_content
	
	def update_chat_details(self, chat_data):
		"""Update panel with details of selected chat."""
		if not chat_data:
			self.details_content.update("Select a chat to view details")
			return
		
		chat_name = chat_data["name"]
		config = gptcli.load_chat_config(chat_name)
		stats = gptcli.load_statistics(chat_name)
		
		# Build details text
		details = []
		details.append(f"[bold]Chat:[/bold] {chat_name}")
		details.append("")
		
		# Settings
		details.append("[bold]Settings:[/bold]")
		model = config.get("model", gptcli.DEFAULT_MODEL)
		details.append(f"  Model: {model}")
		
		system_prompt = config.get("system_prompt")
		if system_prompt:
			if system_prompt in gptcli.SYSTEM_PROMPTS:
				details.append(f"  System Prompt: {system_prompt}")
			else:
				# Custom prompt - show preview
				preview = system_prompt[:40] + "..." if len(system_prompt) > 40 else system_prompt
				details.append(f"  System Prompt: {preview}")
		else:
			details.append("  System Prompt: (default)")
		details.append("")
		
		# Statistics
		details.append("[bold]Statistics:[/bold]")
		details.append(f"  Messages: {chat_data['message_count']}")
		details.append(f"  Requests: {stats['request_count']}")
		details.append(f"  Total Tokens: {stats['total_tokens']:,}")
		details.append(f"  Input Tokens: {stats['total_input_tokens']:,}")
		details.append(f"  Output Tokens: {stats['total_output_tokens']:,}")
		if stats['total_cost'] > 0:
			details.append(f"  Total Cost: ${stats['total_cost']:.6f}")
		if stats['total_time'] > 0:
			details.append(f"  Total Time: {stats['total_time']:.2f}s")
		
		self.details_content.update("\n".join(details))


class ConversationPanel(ScrollableContainer):
	"""Top right panel showing conversation history."""
	
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.border_title = "Conversation"
		self.current_chat_name = None
		self.conversation_container = None
	
	def compose(self) -> ComposeResult:
		self.conversation_container = Container(id="conversation-container")
		yield self.conversation_container
	
	def load_conversation(self, chat_name):
		"""Load and display conversation for selected chat."""
		self.current_chat_name = chat_name
		self.conversation_container.remove_children()
		
		if not chat_name:
			self.conversation_container.mount(Static("Select a chat to view conversation", classes="empty-message"))
			return
		
		messages = gptcli.load_conversation(chat_name)
		
		if not messages:
			self.conversation_container.mount(Static("No messages in this conversation yet.", classes="empty-message"))
			return
		
		# Render messages
		for message in messages:
			role = message.get("role", "user")
			content = message.get("content", "")
			
			if role == "user":
				# User message
				from rich.text import Text
				user_header = Text("You:", style="bold cyan")
				user_content = Text(f"\n{content}")
				user_text = Text.assemble(user_header, user_content)
				user_widget = Static(user_text, classes="message user-message")
				self.conversation_container.mount(user_widget)
			elif role == "assistant":
				# Assistant message with markdown
				config = gptcli.load_chat_config(chat_name)
				model = config.get("model", gptcli.DEFAULT_MODEL)
				# Combine header and content in markdown format
				header = f"**GPT({chat_name}|{model}):**\n\n"
				full_content = header + content
				# Use Markdown widget for the entire message
				assistant_widget = Markdown(full_content, classes="message assistant-message")
				self.conversation_container.mount(assistant_widget)
		
		# Auto-scroll to bottom
		self.scroll_end(animate=False)


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
		
		#left-panel {
			width: 25%;
		}
		
		#chat-list-panel {
			height: 50%;
			border: solid $primary;
			background: $panel;
		}
		
		#chat-details-panel {
			height: 50%;
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
		
		.chat-details-content {
			width: 100%;
			height: 100%;
			padding: 1;
		}
		
		#right-panel {
			width: 75%;
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
		
		#conversation-container {
			width: 100%;
			padding: 1;
		}
		
		.message {
			margin: 1 0;
			padding: 1;
		}
		
		.user-message {
			background: $panel;
			border-left: solid $primary;
		}
		
		.assistant-message {
			background: $surface;
			border-left: solid $success;
			width: 100%;
		}
		
		.empty-message {
			padding: 2;
			text-align: center;
			color: $text-muted;
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
			with Vertical(id="left-panel"):
				yield ChatListPanel(id="chat-list-panel")
				yield ChatDetailsPanel(id="chat-details-panel")
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
		# Update details panel if a chat is selected
		chat_list_panel = self.query_one("#chat-list-panel", ChatListPanel)
		details_panel = self.query_one("#chat-details-panel", ChatDetailsPanel)
		chat_data = chat_list_panel.get_selected_chat()
		if chat_data:
			details_panel.update_chat_details(chat_data)


def main():
	"""Main entry point for the UI application."""
	app = GptCliApp()
	app.run()


if __name__ == "__main__":
	main()

