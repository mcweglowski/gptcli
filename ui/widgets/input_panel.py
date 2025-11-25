from typing import Optional

from textual import events
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Static, TextArea
from rich.text import Text


class MessageInput(TextArea):
	"""Custom TextArea for message input with Enter to send."""
	
	async def _on_key(self, event: events.Key) -> None:
		"""Handle key presses - Enter sends, Shift+Enter adds new line."""
		if event.key == "enter" and not getattr(event, "shift", False):
			message = self.text.strip()
			if message:
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
				self.text = ""
				
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
			else:
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
		self.status_spinner: Optional[Static] = None
		self._spinner_interval = None
		self._spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
		self._spinner_index = 0
		self._spinner_text = "Thinking"
	
	def compose(self) -> ComposeResult:
		with Vertical():
			self.message_input = MessageInput(
				text="",
				id="message-input",
				show_line_numbers=False,
				soft_wrap=True
			)
			yield self.message_input
			self.status_spinner = Static("", id="status-spinner", classes="status-spinner")
			yield self.status_spinner
	
	def show_spinner(self, text: str = "Thinking") -> None:
		"""Show animated spinner with text."""
		if self.status_spinner:
			self._spinner_text = text
			self.status_spinner.update(f"[yellow]{text} {self._spinner_frames[0]}[/yellow]")
			self.status_spinner.visible = True
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
			self.status_spinner.update(f"[yellow]{self._spinner_text} {frame}[/yellow]")

