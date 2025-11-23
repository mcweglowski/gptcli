#!/usr/bin/env python3
"""
Textual-based UI for GPT CLI chat application.
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, Input


class ChatListPanel(Static):
	"""Left panel showing list of available chats."""
	
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.border_title = "Chats"
	
	def compose(self) -> ComposeResult:
		yield Static("Chat list will go here", classes="chat-list-content")


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
			height: 33%;
			border: solid $primary;
			background: $panel;
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


def main():
	"""Main entry point for the UI application."""
	app = GptCliApp()
	app.run()


if __name__ == "__main__":
	main()

