from textual.app import ComposeResult
from textual.containers import ScrollableContainer, Vertical
from textual.message import Message
from textual.widgets import Static, Markdown
from rich.text import Text

import gptcli


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
				user_color = gptcli.USER_COLOR or "cyan"
				user_header = Text(f"{user_name}:", style=f"bold {user_color}")
				user_content = Text(f"\n{content}")
				user_text = Text.assemble(user_header, user_content)
				user_widget = Static(user_text, classes="message user-message")
				# Set border color to match user color
				user_widget.styles.border_left = ("solid", user_color)
				self.conversation_container.mount(user_widget)
			elif role == "assistant":
				# Get model from message if available, otherwise from config
				model = message.get("model")
				if not model:
					config = gptcli.load_chat_config(chat_name)
					model = config.get("model", gptcli.DEFAULT_MODEL)
				assistant_color = gptcli.ASSISTANT_COLOR or "green"
				# Create header with Text (same style as user)
				model_header = Text(f"{model}:", style=f"bold {assistant_color}")
				header_widget = Static(model_header, classes="message assistant-message-header")
				header_widget.styles.border_left = ("solid", assistant_color)
				# Create content with Markdown
				content_widget = Markdown(content, classes="message assistant-message-content")
				content_widget.styles.border_left = ("solid", assistant_color)
				# Mount both widgets directly
				self.conversation_container.mount(header_widget)
				self.conversation_container.mount(content_widget)
		
		self.post_message(ScrollToBottom())

