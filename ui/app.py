#!/usr/bin/env python3
"""
Main application for GPT CLI UI.
"""

import os
import time
from pathlib import Path
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static
from openai import APIError
from rich.text import Text

import gptcli
from .widgets import (
	ChatListPanel,
	ChatDetailsPanel,
	ConversationPanel,
	InputPanel
)


class GptCliApp(App):
	"""Main Textual application for GPT CLI."""
	
	# CSS_PATH should be relative to the module file location
	CSS_PATH = str(Path(__file__).parent / "styles.css")
	
	BINDINGS = [
		("q", "quit", "Quit"),
		("ctrl+c", "quit", "Quit"),
		("escape", "quit", "Quit"),
		("r", "refresh_chats", "Refresh chats"),
	]
	
	def compose(self) -> ComposeResult:
		"""Create child widgets for the app."""
		with Horizontal():
			with Vertical(id="left-panel"):
				yield ChatListPanel(id="chat-list-panel")
				yield ChatDetailsPanel(id="chat-details-panel")
			with Vertical(id="right-panel"):
				yield ConversationPanel(id="conversation-panel")
				yield InputPanel(id="input-panel")
	
	def action_quit(self) -> None:
		"""Quit the application."""
		self.exit()
	
	def action_refresh_chats(self) -> None:
		"""Refresh the chat list."""
		chat_list_panel = self.query_one("#chat-list-panel", ChatListPanel)
		chat_list_panel.load_chats()
	
	def on_mount(self) -> None:
		"""Focus on chat list when app starts."""
		chat_list = self.query_one("#chat-list")
		chat_list.focus()
		# Update details panel if a chat is selected
		chat_list_panel = self.query_one("#chat-list-panel", ChatListPanel)
		details_panel = self.query_one("#chat-details-panel", ChatDetailsPanel)
		chat_data = chat_list_panel.get_selected_chat()
		if chat_data:
			details_panel.update_chat_details(chat_data)
	
	def send_message_to_api(self, chat_name: str, user_message: str) -> None:
		"""Send message to API and update UI - synchronous version."""
		conversation_panel = self.query_one("#conversation-panel", ConversationPanel)
		
		# Load conversation
		messages = gptcli.load_conversation(chat_name)
		
		# Add user message
		messages.append({"role": "user", "content": user_message})
		
		# Save conversation immediately
		gptcli.save_conversation(chat_name, messages)
		
		# Update UI directly - show user message and loading indicator
		conversation_panel.load_conversation(chat_name)
		loading_widget = Static("[yellow]Thinking...[/yellow]", classes="loading-message")
		conversation_panel.conversation_container.mount(loading_widget)
		# Scroll to bottom after a brief delay to ensure widgets are rendered
		conversation_panel.set_timer(0.1, lambda: conversation_panel.scroll_end(animate=False))
		
		# Get chat config
		config = gptcli.load_chat_config(chat_name)
		model = config.get("model", gptcli.DEFAULT_MODEL)
		
		# Get system prompt
		system_prompt = config.get("system_prompt")
		if system_prompt:
			if system_prompt in gptcli.SYSTEM_PROMPTS:
				current_system_prompt = gptcli.SYSTEM_PROMPTS[system_prompt]
			else:
				current_system_prompt = system_prompt  # Custom prompt
		else:
			current_system_prompt = None
		
		# Prepare API messages (last 10)
		api_messages = messages[-10:] if len(messages) > 10 else messages.copy()
		
		# Add system prompt if set
		if current_system_prompt:
			if not api_messages or api_messages[0].get("role") != "system":
				api_messages = [{"role": "system", "content": current_system_prompt}] + api_messages
			else:
				api_messages[0]["content"] = current_system_prompt
		
		# Track statistics
		start_time = time.time()
		
		try:
			# Call API (non-streaming for now)
			response = gptcli.client.responses.create(
				model=model,
				input=api_messages,
				stream=False
			)
			
			# Extract response text
			assistant_message = ""
			if hasattr(response, 'output_text'):
				if isinstance(response.output_text, list) and len(response.output_text) > 0:
					assistant_message = str(response.output_text[0].text) if hasattr(response.output_text[0], 'text') else str(response.output_text[0])
				else:
					assistant_message = str(response.output_text)
			elif hasattr(response, 'text'):
				assistant_message = str(response.text)
			else:
				assistant_message = str(response)
			
			# Add assistant message to conversation
			messages.append({"role": "assistant", "content": assistant_message})
			gptcli.save_conversation(chat_name, messages)
			
			# Calculate statistics
			elapsed_time = time.time() - start_time
			input_tokens = 0
			output_tokens = 0
			total_tokens = 0
			cost = 0.0
			
			if hasattr(response, 'usage'):
				usage = response.usage
				input_tokens = getattr(usage, 'input_tokens', 0) or getattr(usage, 'prompt_tokens', 0) or 0
				output_tokens = getattr(usage, 'output_tokens', 0) or getattr(usage, 'completion_tokens', 0) or 0
				total_tokens = getattr(usage, 'total_tokens', 0) or (input_tokens + output_tokens)
			
			# Calculate cost
			if input_tokens > 0 or output_tokens > 0:
				cost = gptcli.calculate_cost(model, input_tokens, output_tokens)
			
			# Update statistics
			gptcli.update_statistics(chat_name, input_tokens, output_tokens, total_tokens, cost, elapsed_time)
			
			# Update UI directly - remove loading indicator and reload conversation
			conversation_panel.load_conversation(chat_name)
			# Scroll to bottom - use multiple attempts to ensure it works
			# load_conversation already has scroll_end, but add extra attempts
			def force_scroll():
				try:
					conversation_panel.scroll_end(animate=False)
				except:
					pass
			conversation_panel.call_after_refresh(force_scroll)
			conversation_panel.set_timer(0.2, force_scroll)
			conversation_panel.set_timer(0.5, force_scroll)  # Extra backup
			
			# Update details panel (don't refresh chat list to preserve selection)
			chat_list_panel = self.query_one("#chat-list-panel", ChatListPanel)
			details_panel = self.query_one("#chat-details-panel", ChatDetailsPanel)
			# Get fresh chat data
			chat_data = chat_list_panel.get_selected_chat()
			if not chat_data or chat_data["name"] != chat_name:
				# If selection was lost, restore it
				chat_list_panel.load_chats(preserve_selection=True)
				chat_data = chat_list_panel.get_selected_chat()
			
			if chat_data:
				details_panel.update_chat_details(chat_data)
			
			# Focus back on input
			input_panel = self.query_one("#input-panel", InputPanel)
			input_panel.message_input.focus()
			
		except APIError as e:
			# Remove loading indicator
			conversation_panel.load_conversation(chat_name)
			# Show error message
			error_msg = f"API Error: {str(e)}"
			error_text = Text(f"Error: {error_msg}", style="red")
			error_widget = Static(error_text, classes="error-message")
			conversation_panel.conversation_container.mount(error_widget)
			conversation_panel.scroll_end(animate=False)
			# Focus back on input
			input_panel = self.query_one("#input-panel", InputPanel)
			input_panel.message_input.focus()
		except Exception as e:
			# Remove loading indicator
			conversation_panel.load_conversation(chat_name)
			# Show error message
			error_msg = f"Error: {str(e)}"
			error_text = Text(f"Error: {error_msg}", style="red")
			error_widget = Static(error_text, classes="error-message")
			conversation_panel.conversation_container.mount(error_widget)
			conversation_panel.scroll_end(animate=False)
			# Focus back on input
			input_panel = self.query_one("#input-panel", InputPanel)
			input_panel.message_input.focus()

