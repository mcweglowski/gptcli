from textual.app import ComposeResult
from textual.containers import Vertical, Center, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Label, Button, TextArea


class EditSystemPromptModal(ModalScreen):
	"""Modal dialog for editing system prompt."""
	
	BINDINGS = [
		("escape", "cancel", "Cancel"),
	]
	
	def __init__(self, chat_name: str, current_prompt: str = "", *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.chat_name = chat_name
		self.current_prompt = current_prompt or ""
	
	def compose(self) -> ComposeResult:
		with Center():
			with Vertical(id="modal-dialog", classes="modal-content"):
				yield Label(f"System prompt for {self.chat_name}:", classes="modal-title")
				self.prompt_input = TextArea(
					text=self.current_prompt,
					id="system-prompt-edit-input",
					show_line_numbers=False,
					soft_wrap=True
				)
				yield self.prompt_input
				with Horizontal(classes="modal-buttons"):
					self.save_button = Button("Save", id="modal-save", variant="primary")
					yield self.save_button
					self.cancel_button = Button("Cancel", id="modal-cancel")
					yield self.cancel_button
	
	def on_mount(self) -> None:
		self.prompt_input.focus()
	
	def on_button_pressed(self, event) -> None:
		if event.button.id == "modal-save":
			self.dismiss(self.prompt_input.text.strip())
		elif event.button.id == "modal-cancel":
			self.dismiss(None)
	
	def action_cancel(self) -> None:
		self.dismiss(None)

