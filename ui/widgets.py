#!/usr/bin/env python3
"""
UI widgets for GPT CLI application.
"""

from textual.containers import Container, ScrollableContainer, Vertical, Horizontal, Center
from textual.widgets import Static, TextArea, ListView, ListItem, Label, Markdown, Input, Button
from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.screen import ModalScreen
from rich.text import Text
from typing import Optional
import os

import gptcli
from .utils import format_chat_entry


class ScrollToBottom(Message):
	"""Message to scroll conversation to bottom."""
	def __init__(self):
		super().__init__()


class ChatListItem(ListItem):
	"""List item for a chat."""

	
	def __init__(self, chat_data, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.chat_data = chat_data
	
	def compose(self):
		yield Label(format_chat_entry(self.chat_data))


class ChatListPanel(Container):
	"""Left panel showing list of available chats."""
	
	BINDINGS = [
		Binding("n", "new_chat", "New chat"),
		Binding("d", "delete_chat", "Delete chat"),
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
	
	def load_chats(self, preserve_selection: bool = True) -> None:
		"""Load and display available chats."""
		# Remember currently selected chat
		selected_chat_name = None
		if preserve_selection:
			chat_data = self.get_selected_chat()
			if chat_data:
				selected_chat_name = chat_data["name"]
		
		from .utils import get_available_chats
		chats = get_available_chats()
		self.chat_list_view.clear()
		for chat in chats:
			self.chat_list_view.append(ChatListItem(chat))
		
		# Restore selection if it still exists
		if selected_chat_name and preserve_selection:
			# Find the chat in the list and select it
			self._restore_selection(selected_chat_name)
	
	def _restore_selection(self, chat_name: str) -> None:
		"""Restore selection after loading chats."""
		for i, item in enumerate(self.chat_list_view.children):
			if isinstance(item, ChatListItem) and item.chat_data["name"] == chat_name:
				# Set the index to restore selection
				self.chat_list_view.index = i
				# Update details panel
				self.update_details_on_selection()
				# Also update conversation panel
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
		# Get the app instance to update details panel
		app = self.app
		if app:
			details_panel = app.query_one("#chat-details-panel", ChatDetailsPanel)
			chat_data = self.get_selected_chat()
			details_panel.update_chat_details(chat_data)
			
	def action_new_chat(self) -> None:
		app = self.app
		if not app:
			return
		
		def handle_result(chat_name: Optional[str]) -> None:
			"""Handle result from modal - create new chat and set it as active."""
			if not chat_name or not chat_name.strip():
				return  # User cancelled or entered empty name
			
			chat_name = chat_name.strip()
			
			# Check if chat already exists
			chat_path = gptcli.get_conversation_path(chat_name)
			if os.path.exists(chat_path):
				# Chat already exists - could show error, but for now just select it
				app.bell()
				self.load_chats()
				self._restore_selection(chat_name)
				return
			
			# Create new chat file (empty conversation)
			gptcli.save_conversation(chat_name, [])
			
			# Reload chats and select the new one
			self.load_chats(preserve_selection=False)
			self._restore_selection(chat_name)
			
			# Focus on input panel for first message
			# Use call_after_refresh to ensure UI is updated
			def focus_input():
				input_panel = app.query_one("#input-panel", InputPanel)
				if input_panel.message_input:
					input_panel.message_input.focus()
			
			app.call_after_refresh(focus_input)
		
		app.push_screen(NewChatModal(), handle_result)
	
	def action_delete_chat(self) -> None:
		"""Delete selected chat."""
		chat_data = self.get_selected_chat()
		if not chat_data:
			app = self.app
			if app:
				app.bell()  # No chat selected
			return
		
		chat_name = chat_data["name"]
		app = self.app
		if not app:
			return
		
		def handle_result(confirmed: Optional[bool]) -> None:
			"""Handle result from delete confirmation modal."""
			if not confirmed:
				return  # User cancelled
			
			# Delete chat files
			chat_path = gptcli.get_conversation_path(chat_name)
			config_path = gptcli.get_chat_config_path(chat_name)
			stats_path = gptcli.get_stats_path(chat_name)
			
			if os.path.exists(chat_path):
				os.remove(chat_path)
			if os.path.exists(config_path):
				os.remove(config_path)
			if os.path.exists(stats_path):
				os.remove(stats_path)
			
			# Reload chats
			self.load_chats(preserve_selection=False)
			
			# Clear conversation panel
			conversation_panel = app.query_one("#conversation-panel", ConversationPanel)
			conversation_panel.load_conversation(None)
			
			# Clear details panel
			details_panel = app.query_one("#chat-details-panel", ChatDetailsPanel)
			details_panel.update_chat_details(None)
		
		app.push_screen(DeleteChatModal(chat_name), handle_result)


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
		self.conversation_container = Vertical(id="conversation-container")
		yield self.conversation_container
	
	def on_scroll_to_bottom(self, event: ScrollToBottom) -> None:
		"""Handle scroll to bottom message."""
		# Use multiple attempts to ensure scrolling works
		def scroll_to_bottom():
			try:
				self.scroll_end(animate=False)
			except:
				pass
		
		# Try after refresh
		self.call_after_refresh(scroll_to_bottom)
		# Also try with timers as backup
		self.set_timer(0.1, scroll_to_bottom)
		self.set_timer(0.3, scroll_to_bottom)
		self.set_timer(0.5, scroll_to_bottom)
	
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
		
		# Render all messages from oldest to newest
		# Messages are already in chronological order in the file
		for message in messages:
			role = message.get("role", "user")
			content = message.get("content", "")
			
			if role == "user":
				# User message
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
		
		# Post message to scroll to bottom after all widgets are mounted
		# This ensures scrolling happens after layout is complete
		self.post_message(ScrollToBottom())


class MessageInput(TextArea):
	"""Custom TextArea for message input with Enter to send."""
	
	def on_key(self, event) -> None:
		"""Handle key presses - Enter sends, Shift+Enter adds new line."""
		if event.key == "enter":
			# Check if Shift is pressed by examining the key name
			# In Textual, Shift+Enter might be represented differently
			# For now, we'll always send on Enter and let user use Shift+Enter for newlines
			# (TextArea should handle Shift+Enter automatically)
			
			# Regular Enter - send message
			message = self.text.strip()
			if message:
				# Get current chat BEFORE clearing input
				app = self.app
				if not app:
					return
				
				chat_list_panel = app.query_one("#chat-list-panel", ChatListPanel)
				chat_data = chat_list_panel.get_selected_chat()
				
				if not chat_data:
					# No chat selected - show some feedback?
					event.prevent_default()
					event.stop()
					return
				
				chat_name = chat_data["name"]
				
				# Clear input
				self.text = ""
				
				# Send message asynchronously
				# @work decorator handles async execution
				try:
					app.send_message_to_api(chat_name, message)
				except Exception as e:
					# Show error if function call fails
					conversation_panel = app.query_one("#conversation-panel", ConversationPanel)
					error_text = Text(f"Error calling API: {str(e)}", style="red")
					error_widget = Static(error_text, classes="error-message")
					conversation_panel.conversation_container.mount(error_widget)
				event.prevent_default()
				event.stop()
			else:
				# Empty message - prevent default to avoid newline
				event.prevent_default()
				event.stop()
			# If Shift+Enter, allow default behavior (newline)


class InputPanel(Container):
	"""Bottom right panel for user input."""
	
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.border_title = "Input"
		self.message_input = None
		self.status_spinner = None
		self._spinner_interval = None
		self._spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
		self._spinner_index = 0
		self._spinner_text = "Thinking"
	
	def compose(self) -> ComposeResult:
		from textual.containers import Vertical
		# Container for input and spinner
		with Vertical():
			# Use custom TextArea for multi-line input with word wrap
			self.message_input = MessageInput(
				text="",
				id="message-input",
				show_line_numbers=False,
				soft_wrap=True
			)
			yield self.message_input
			# Status spinner in bottom right corner
			self.status_spinner = Static("", id="status-spinner", classes="status-spinner")
			yield self.status_spinner
	
	def show_spinner(self, text: str = "Thinking") -> None:
		"""Show animated spinner with text."""
		if self.status_spinner:
			self._spinner_text = text
			self.status_spinner.update(f"[yellow]{text} {self._spinner_frames[0]}[/yellow]")
			self.status_spinner.visible = True
			# Start animation
			self._spinner_index = 0
			if self._spinner_interval is None:
				self._spinner_interval = self.set_interval(0.1, self._animate_spinner)
	
	def hide_spinner(self) -> None:
		"""Hide spinner."""
		if self.status_spinner:
			self.status_spinner.visible = False
			if self._spinner_interval:
				self._spinner_interval.stop()
				self._spinner_interval = None
	
	def _animate_spinner(self) -> None:
		"""Animate spinner frame."""
		if self.status_spinner and self.status_spinner.visible:
			self._spinner_index = (self._spinner_index + 1) % len(self._spinner_frames)
			frame = self._spinner_frames[self._spinner_index]
			# Use stored text
			self.status_spinner.update(f"[yellow]{self._spinner_text} {frame}[/yellow]")

class NewChatModal(ModalScreen):
	"""Modal dialog for creating new chat."""
	
	BINDINGS = [
		("escape", "cancel", "Cancel"),
	]
	
	def compose(self) -> ComposeResult:
		"""Create modal content."""
		with Center():
			with Vertical(id="modal-dialog", classes="modal-content"):
				yield Label("Enter chat name:", id="modal-title", classes="modal-title")
				self.name_input = Input(
					placeholder="Chat name...",
					id="chat-name-input"
				)
				yield self.name_input
				with Horizontal(classes="modal-buttons"):
					self.yes_button = Button("Yes", id="modal-ok", variant="primary")
					yield self.yes_button
					self.no_button = Button("No", id="modal-cancel")
					yield self.no_button
	
	def on_mount(self) -> None:
		"""Focus input when modal opens."""
		self.name_input.focus()
		# Ensure buttons have visible text
		if hasattr(self, 'yes_button'):
			self.yes_button.label = "Yes"
		if hasattr(self, 'no_button'):
			self.no_button.label = "No"
	
	def on_button_pressed(self, event) -> None:
		"""Handle button presses."""
		if event.button.id == "modal-ok":
			chat_name = self.name_input.value.strip()
			if chat_name:
				self.dismiss(chat_name)
			else:
				self.app.bell()
		elif event.button.id == "modal-cancel":
			self.dismiss(None)
	
	def on_input_submitted(self, event) -> None:
		"""Handle Enter key in input."""
		if event.input.id == "chat-name-input":
			chat_name = event.input.value.strip()
			if chat_name:
				self.dismiss(chat_name)
			else:
				self.app.bell()
	
	def action_cancel(self) -> None:
		"""Cancel modal."""
		self.dismiss(None)


class DeleteChatModal(ModalScreen):
	"""Modal dialog for confirming chat deletion."""
	
	BINDINGS = [
		("escape", "cancel", "Cancel"),
	]
	
	def __init__(self, chat_name: str, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.chat_name = chat_name
	
	def compose(self) -> ComposeResult:
		"""Create modal content."""
		with Center():
			with Vertical(id="modal-dialog", classes="modal-content"):
				yield Label(
					f'Czy chcesz usunąć "{self.chat_name}"?',
					id="modal-title",
					classes="modal-title"
				)
				with Horizontal(classes="modal-buttons"):
					self.yes_button = Button("Yes", id="modal-yes", variant="primary")
					yield self.yes_button
					self.no_button = Button("No", id="modal-no")
					yield self.no_button
	
	def on_mount(self) -> None:
		"""Ensure buttons have visible text."""
		if hasattr(self, 'yes_button'):
			self.yes_button.label = "Yes"
		if hasattr(self, 'no_button'):
			self.no_button.label = "No"
	
	def on_button_pressed(self, event) -> None:
		"""Handle button presses."""
		if event.button.id == "modal-yes":
			self.dismiss(True)
		elif event.button.id == "modal-no":
			self.dismiss(False)
	
	def action_cancel(self) -> None:
		"""Cancel modal."""
		self.dismiss(False)

