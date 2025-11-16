import argparse
import json
import os
import time
from openai import OpenAI
from openai import APIError
from rich.console import Console
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.live import Live

client = OpenAI()
console = Console()

MODEL = "gpt-5.1"

USER_COLOR = "\033[96m"
ASSISTANT_COLOR = "\033[92m"
RESET_COLOR = "\033[0m"

CONVERSATIONS_DIR = "conversations"


def get_conversation_path(chat_name):
	"""Returns the path to the conversation file."""
	if not os.path.exists(CONVERSATIONS_DIR):
		os.makedirs(CONVERSATIONS_DIR)
	return os.path.join(CONVERSATIONS_DIR, f"{chat_name}.json")


def load_conversation(chat_name):
	"""Loads all conversation messages from file."""
	file_path = get_conversation_path(chat_name)
	if not os.path.exists(file_path):
		return []
	
	try:
		with open(file_path, 'r', encoding='utf-8') as f:
			data = json.load(f)
		# Handle legacy format where file might contain a string instead of list
		if isinstance(data, str):
			return []
		# Ensure it's a list
		if not isinstance(data, list):
			return []
		# Return all messages (we'll use last 10 for API, but save all)
		return data
	except (json.JSONDecodeError, IOError):
		return []


def save_conversation(chat_name, messages):
	"""Saves conversation to file."""
	file_path = get_conversation_path(chat_name)
	try:
		with open(file_path, 'w', encoding='utf-8') as f:
			json.dump(messages, f, ensure_ascii=False, indent=2)
	except IOError:
		print(f"{RESET_COLOR}Error: Could not save conversation to {file_path}")


def main():
	parser = argparse.ArgumentParser(description='Console GPT chat')
	parser.add_argument('--chat', '-c', type=str, help='Chat name (optional)')
	args = parser.parse_args()
	
	chat_name = args.chat
	messages = []
	
	# Load conversation if chat name is provided
	if chat_name:
		messages = load_conversation(chat_name)
		if messages:
			print(f"{ASSISTANT_COLOR}Loaded conversation: {chat_name} ({len(messages)} messages){RESET_COLOR}")
		else:
			print(f"{ASSISTANT_COLOR}Starting new conversation: {chat_name}{RESET_COLOR}")
	else:
		print("Console GPT chat (temporary conversation - not saved). Type 'exit' or 'quit' to finish.")
	
	while True:
		user_input = input(f"{USER_COLOR}You: ")
		if user_input.lower() in ("exit", "quit"):
			break

		print(RESET_COLOR)

		messages.append({"role": "user", "content":user_input})

		# Use only last 10 messages for API to avoid token limits
		api_messages = messages[-10:] if len(messages) > 10 else messages

		# Try streaming first, fallback to regular if not supported
		full_response = ""
		print(f"{ASSISTANT_COLOR}GPT: {RESET_COLOR}")
		
		try:
			# Try streaming mode
			stream = client.responses.create(
				model=MODEL,
				input=api_messages,
				stream=True
			)
			
			# Stream response token by token
			with Live(console=console, refresh_per_second=10) as live:
				for event in stream:
					text = ""
					
					# Debug: print event type and attributes (remove after debugging)
					event_type = getattr(event, 'type', '')
					
					# For text delta events, extract the delta attribute
					if isinstance(event_type, str) and ('text.delta' in event_type or 'output_text.delta' in event_type):
						# This is a text delta event - extract delta
						if hasattr(event, 'delta'):
							delta_value = event.delta
							if delta_value is not None:
								text = str(delta_value)
					# Also check for delta attribute directly (fallback for other event types)
					elif hasattr(event, 'delta'):
						delta = event.delta
						if delta is not None:
							if isinstance(delta, str):
								text = delta
							elif hasattr(delta, 'content'):
								text = str(delta.content) if delta.content else ""
							else:
								text = str(delta)
					# Handle other event types that might contain text
					elif hasattr(event, 'output_text'):
						text = str(event.output_text) if event.output_text else ""
					elif isinstance(event, dict):
						text = event.get('delta', event.get('output_text', event.get('content', '')))
					
					if text:
						full_response += text
						# Update live display with accumulated response
						live.update(Markdown(full_response))
			
			# Print final response (in case Live didn't preserve it)
			if full_response:
				console.print(Markdown(full_response))
			else:
				print(f"{RESET_COLOR}No response received.{RESET_COLOR}")
			
		except APIError as e:
			# Handle API errors (rate limits, token limits, etc.)
			print(f"{RESET_COLOR}Error: {e.message}{RESET_COLOR}")
			print(f"{RESET_COLOR}Try reducing the conversation length or wait a moment.{RESET_COLOR}")
			# Don't save this failed attempt
			messages.pop()  # Remove the user message that failed
			continue
			
		except (TypeError, AttributeError) as e:
			# Fallback to non-streaming if stream=True is not supported
			# Show progress bar while waiting for response
			with Progress(
				SpinnerColumn(),
				TextColumn("[progress.description]{task.description}"),
				TimeElapsedColumn(),
				console=console,
				transient=True
			) as progress:
				task = progress.add_task("[cyan]Thinking...", total=None)
				try:
					response = client.responses.create(
						model=MODEL,
						input=api_messages
					)
					full_response = response.output_text
					console.print(Markdown(full_response))
				except APIError as api_err:
					print(f"{RESET_COLOR}Error: {api_err.message}{RESET_COLOR}")
					messages.pop()  # Remove the user message that failed
					continue
		
		print(RESET_COLOR, end="")

		messages.append({"role": "assistant", "content": full_response})
		
		# Save after receiving response
		if chat_name:
			save_conversation(chat_name, messages)

if __name__ == "__main__":
	main()