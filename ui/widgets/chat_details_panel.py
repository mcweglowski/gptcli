from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static

import gptcli


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
		
		details = []
		details.append(f"[bold]Chat:[/bold] {chat_name}")
		details.append("")
		details.append("[bold]Settings:[/bold]")
		model = config.get("model", gptcli.DEFAULT_MODEL)
		details.append(f"  Model: {model}")
		
		system_prompt = config.get("system_prompt")
		if system_prompt:
			if system_prompt in gptcli.SYSTEM_PROMPTS:
				details.append(f"  System Prompt: {system_prompt}")
			else:
				preview = system_prompt[:40] + "..." if len(system_prompt) > 40 else system_prompt
				details.append(f"  System Prompt: {preview}")
		else:
			details.append("  System Prompt: (default)")
		details.append("")
		
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

