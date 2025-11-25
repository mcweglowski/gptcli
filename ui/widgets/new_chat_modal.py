from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, Center
from textual.screen import ModalScreen
from textual.widgets import Label, Input, Button


class NewChatModal(ModalScreen):
	"""Modal dialog for creating new chat."""
	
	BINDINGS = [
		("escape", "cancel", "Cancel"),
	]
	
	def compose(self) -> ComposeResult:
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

