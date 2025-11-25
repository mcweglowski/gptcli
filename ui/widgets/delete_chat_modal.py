from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, Center
from textual.screen import ModalScreen
from textual.widgets import Label, Button


class DeleteChatModal(ModalScreen):
	"""Modal dialog for confirming chat deletion."""
	
	BINDINGS = [
		("escape", "cancel", "Cancel"),
	]
	
	def __init__(self, chat_name: str, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.chat_name = chat_name
	
	def compose(self) -> ComposeResult:
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

