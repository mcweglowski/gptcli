from typing import Optional

from textual import events
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Static, TextArea
from rich.text import Text



class MessageInput(TextArea):
	"""Custom TextArea for message input with Enter to send."""
	
	async def on_key(self, event: events.Key) -> None:
		key = event.key  # np. "enter", "return", "shift+enter", "ctrl+c", "a" itd.
		
		# Shift+Enter - wstaw nową linię
		if key in ("shift+enter", "shift+return"):
			self.insert('\n')
			event.prevent_default()
			event.stop()
			return
		
		# Enter bez Shift - wyślij wiadomość
		if key in ("enter", "return"):
			message = self.text.strip()
			if not message:
				event.prevent_default()
				event.stop()
				return
			
			app = self.app
			if not app:
				return
			
			chat_list_panel = app.query_one("#chat-list-panel")
			chat_data = getattr(chat_list_panel, "get_selected_chat", lambda: None)()
			
			if not chat_data:
				event.prevent_default()
				event.stop()
				return
			
			chat_name = chat_data["name"]
			self.text = ""  # wyczyść input po wysłaniu
			
			try:
				app.send_message_to_api(chat_name, message)
			except Exception as exc:
				conversation_panel = app.query_one("#conversation-panel")
				error_text = Text(f"Error calling API: {str(exc)}", style="red")
				error_widget = Static(error_text, classes="error-message")
				conversation_container = getattr(conversation_panel, "conversation_container", None)
				if conversation_container:
					conversation_container.mount(error_widget)
			
			event.prevent_default()
			event.stop()
			return
		
		await super()._on_key(event)


class InputPanel(Container):
	"""Bottom right panel for user input."""
	
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.border_title = "Input"
		self.message_input: Optional[MessageInput] = None
	
	def compose(self) -> ComposeResult:
		with Vertical():
			self.message_input = MessageInput(
				text="",
				id="message-input",
				show_line_numbers=False,
				soft_wrap=True
			)
			yield self.message_input

