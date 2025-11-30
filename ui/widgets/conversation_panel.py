from textual.app import ComposeResult
from textual.containers import ScrollableContainer, Vertical, Horizontal
from textual.message import Message
from textual.widgets import Static, Markdown
from rich.text import Text

import gptcli


class AnimatedThinkingMessage(Static):
	"""Animated 'Thinking' message with spinner."""
	
	SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
	
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._spinner_index = 0
		self._spinner_interval = None
	
	def on_mount(self) -> None:
		"""Start animation when widget is mounted."""
		self._spinner_index = 0
		self._update_text()
		# Use smaller interval for smoother animation (0.05s instead of 0.1s)
		self._spinner_interval = self.set_interval(0.05, self._animate)
	
	def on_unmount(self) -> None:
		"""Stop animation when widget is unmounted."""
		if self._spinner_interval:
			self._spinner_interval.stop()
			self._spinner_interval = None
	
	def _animate(self) -> None:
		"""Animate spinner frame."""
		self._spinner_index = (self._spinner_index + 1) % len(self.SPINNER_FRAMES)
		self._update_text()
	
	def _update_text(self) -> None:
		"""Update text with current spinner frame."""
		frame = self.SPINNER_FRAMES[self._spinner_index]
		self.update(f"[yellow]Thinking {frame}[/yellow]")


class ScrollToBottom(Message):
	"""Message to scroll conversation to bottom."""
	
	def __init__(self):
		super().__init__()


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
		def scroll_to_bottom():
			try:
				self.scroll_end(animate=False)
			except Exception:
				pass
		
		self.call_after_refresh(scroll_to_bottom)
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
		
		for message in messages:
			role = message.get("role", "user")
			content = message.get("content", "")
			
			if role == "user":
				user_name = gptcli.USER_NAME or "You"
				timestamp = message.get("request_timestamp", "")
				
				# Create header with Horizontal container
				header_container = Horizontal()
				
				# Mount header container first
				self.conversation_container.mount(header_container)
				
				# Create Static with user name inside Horizontal (mounted first)
				name_widget = Static(user_name, classes="message-header-left")
				header_container.mount(name_widget)
				
				# Create Static with date inside Horizontal
				date_widget = Static(timestamp, classes="message-header-right")
				header_container.mount(date_widget)
				
				# Create content
				content_widget = Static(content, classes="message user-message-content")
				self.conversation_container.mount(content_widget)
			elif role == "assistant":
				# Get model from message if available, otherwise from config
				model = message.get("model")
				if not model:
					config = gptcli.load_chat_config(chat_name)
					model = config.get("model", gptcli.DEFAULT_MODEL)
				timestamp = message.get("response_timestamp", "")
				
				# Create header with Horizontal container
				header_container = Horizontal()
				
				# Mount header container first
				self.conversation_container.mount(header_container)
				
				# Create Static with model name inside Horizontal (mounted first)
				name_widget = Static(model, classes="message-header-left")
				header_container.mount(name_widget)
				
				# Create Static with date inside Horizontal
				date_widget = Static(timestamp, classes="message-header-right")
				header_container.mount(date_widget)
				
				# Create content with Markdown
				content_widget = Markdown(content, classes="message assistant-message-content")
				self.conversation_container.mount(content_widget)
		
		self.post_message(ScrollToBottom())

