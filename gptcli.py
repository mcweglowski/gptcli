import argparse
import json
import os
import time
from copy import deepcopy
from openai import OpenAI
from openai import APIError
from rich.console import Console
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.live import Live

client = OpenAI()
console = Console()

USER_COLOR = "\033[96m"
ASSISTANT_COLOR = "\033[92m"
RESET_COLOR = "\033[0m"

CONVERSATIONS_DIR = "conversations"
CONFIG_PATH = os.environ.get("GPTCLI_CONFIG_PATH", "config.json")

DEFAULT_CONFIG = {
	"default_model": "gpt-5.1",
	"pricing": {
		"gpt-5.1": {"input": 2.50, "output": 10.00}
	}
}


def ensure_config_file():
	"""Create config file with defaults if it doesn't exist."""
	if os.path.exists(CONFIG_PATH):
		return
	try:
		with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
			json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
	except IOError:
		print(f"{RESET_COLOR}Warning: Could not write config file at {CONFIG_PATH}. Using defaults only.")


def load_config():
	"""Load configuration from file or fall back to defaults."""
	ensure_config_file()
	try:
		with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
			data = json.load(f)
	except (IOError, json.JSONDecodeError):
		return deepcopy(DEFAULT_CONFIG)
	
	config = deepcopy(DEFAULT_CONFIG)
	if isinstance(data, dict):
		if isinstance(data.get("pricing"), dict):
			config["pricing"].update(data["pricing"])
		if isinstance(data.get("default_model"), str):
			config["default_model"] = data["default_model"]
	return config


CONFIG = load_config()
MODEL = CONFIG.get("default_model", DEFAULT_CONFIG["default_model"])
MODEL_PRICING = CONFIG.get("pricing", DEFAULT_CONFIG["pricing"])


def calculate_cost(model, input_tokens, output_tokens):
	"""Calculate cost based on model and token usage."""
	if model not in MODEL_PRICING:
		return None
	pricing = MODEL_PRICING[model]
	input_cost = (input_tokens / 1_000_000) * pricing["input"]
	output_cost = (output_tokens / 1_000_000) * pricing["output"]
	return input_cost + output_cost


def format_statistics(input_tokens, output_tokens, total_tokens, cost, elapsed_time):
	"""Format statistics for display."""
	stats = []
	
	if total_tokens:
		stats.append(f"Tokens: {total_tokens:,} ({input_tokens:,} in / {output_tokens:,} out)")
	
	if cost is not None:
		stats.append(f"Cost: ${cost:.6f}")
	
	if elapsed_time:
		stats.append(f"Time: {elapsed_time:.2f}s")
	
	return " | ".join(stats) if stats else ""


def get_conversation_path(chat_name):
	"""Returns the path to the conversation file."""
	if not os.path.exists(CONVERSATIONS_DIR):
		os.makedirs(CONVERSATIONS_DIR)
	return os.path.join(CONVERSATIONS_DIR, f"{chat_name}.json")


def get_stats_path(chat_name):
	"""Returns the path to the statistics file."""
	if not os.path.exists(CONVERSATIONS_DIR):
		os.makedirs(CONVERSATIONS_DIR)
	# Create statistics subdirectory
	stats_dir = os.path.join(CONVERSATIONS_DIR, "statistics")
	if not os.path.exists(stats_dir):
		os.makedirs(stats_dir)
	return os.path.join(stats_dir, f"{chat_name}.json")


def load_statistics(chat_name):
	"""Loads statistics from file."""
	file_path = get_stats_path(chat_name)
	if not os.path.exists(file_path):
		return {
			"total_input_tokens": 0,
			"total_output_tokens": 0,
			"total_tokens": 0,
			"total_cost": 0.0,
			"total_time": 0.0,
			"request_count": 0
		}
	
	try:
		with open(file_path, 'r', encoding='utf-8') as f:
			data = json.load(f)
		# Ensure all required fields exist
		stats = {
			"total_input_tokens": data.get("total_input_tokens", 0),
			"total_output_tokens": data.get("total_output_tokens", 0),
			"total_tokens": data.get("total_tokens", 0),
			"total_cost": data.get("total_cost", 0.0),
			"total_time": data.get("total_time", 0.0),
			"request_count": data.get("request_count", 0)
		}
		return stats
	except (json.JSONDecodeError, IOError):
		# Return default stats if file is corrupted
		return {
			"total_input_tokens": 0,
			"total_output_tokens": 0,
			"total_tokens": 0,
			"total_cost": 0.0,
			"total_time": 0.0,
			"request_count": 0
		}


def save_statistics(chat_name, stats):
	"""Saves statistics to file."""
	file_path = get_stats_path(chat_name)
	try:
		with open(file_path, 'w', encoding='utf-8') as f:
			json.dump(stats, f, ensure_ascii=False, indent=2)
	except IOError:
		print(f"{RESET_COLOR}Error: Could not save statistics to {file_path}")


def update_statistics(chat_name, input_tokens, output_tokens, total_tokens, cost, elapsed_time):
	"""Updates statistics for a conversation."""
	if not chat_name:
		return  # Don't save stats for temporary conversations
	
	stats = load_statistics(chat_name)
	
	# Add new statistics
	stats["total_input_tokens"] += input_tokens
	stats["total_output_tokens"] += output_tokens
	stats["total_tokens"] += total_tokens
	if cost is not None:
		stats["total_cost"] += cost
	stats["total_time"] += elapsed_time
	stats["request_count"] += 1
	
	# Save updated statistics
	save_statistics(chat_name, stats)


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
		print(f"{ASSISTANT_COLOR}Using model: {MODEL}{RESET_COLOR}")
	else:
		print("Console GPT chat (temporary conversation - not saved). Type 'exit' or 'quit' to finish.")
		print(f"{ASSISTANT_COLOR}Using model: {MODEL}{RESET_COLOR}")
	
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
		
		# Track statistics
		start_time = time.time()
		input_tokens = 0
		output_tokens = 0
		total_tokens = 0
		usage_info = None
		
		try:
			# Show progress bar while waiting for stream to start
			with Progress(
				SpinnerColumn(),
				TextColumn("[progress.description]{task.description}"),
				TimeElapsedColumn(),
				console=console,
				transient=True
			) as progress:
				task = progress.add_task("[cyan]Thinking...", total=None)
				# Start streaming request
				stream = client.responses.create(
					model=MODEL,
					input=api_messages,
					stream=True
				)
				# Get first event to know when stream starts
				stream_iter = iter(stream)
				first_event = next(stream_iter, None)
			
			# Stream response token by token with Live display
			with Live(console=console, refresh_per_second=10) as live:
				response_displayed = False
				# Process first event if we got it
				# Look for usage information in events
				if first_event:
					event = first_event
					text = ""
					
					event_type = getattr(event, 'type', '')
					
					# For text delta events, extract the delta attribute
					if isinstance(event_type, str) and ('text.delta' in event_type or 'output_text.delta' in event_type):
						if hasattr(event, 'delta'):
							delta_value = event.delta
							if delta_value is not None:
								text = str(delta_value)
					elif hasattr(event, 'delta'):
						delta = event.delta
						if delta is not None:
							if isinstance(delta, str):
								text = delta
							elif hasattr(delta, 'content'):
								text = str(delta.content) if delta.content else ""
							else:
								text = str(delta)
					elif hasattr(event, 'output_text'):
						text = str(event.output_text) if event.output_text else ""
					elif isinstance(event, dict):
						text = event.get('delta', event.get('output_text', event.get('content', '')))
					
					if text:
						full_response += text
						live.update(Markdown(full_response))
				
				# Process remaining events
				for event in stream_iter:
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
						response_displayed = True
					
					# Check for usage information in events
					if hasattr(event, 'usage'):
						usage_info = event.usage
					elif hasattr(event, 'response') and hasattr(event.response, 'usage'):
						usage_info = event.response.usage
			
			# Extract usage information from stream if available
			# Try to get it from the stream object or last event
			if hasattr(stream, 'usage'):
				usage_info = stream.usage
			
			# If nothing was streamed, let the user know
			if not full_response:
				print(f"{RESET_COLOR}No response received.{RESET_COLOR}")
			elif not response_displayed:
				# Fallback: show the accumulated response if Live didn't render
				console.print(Markdown(full_response))
			
			# Extract token information from usage
			if usage_info:
				if hasattr(usage_info, 'input_tokens'):
					input_tokens = usage_info.input_tokens
				elif isinstance(usage_info, dict):
					input_tokens = usage_info.get('input_tokens', usage_info.get('prompt_tokens', 0))
				
				if hasattr(usage_info, 'output_tokens'):
					output_tokens = usage_info.output_tokens
				elif isinstance(usage_info, dict):
					output_tokens = usage_info.get('output_tokens', usage_info.get('completion_tokens', 0))
				
				if hasattr(usage_info, 'total_tokens'):
					total_tokens = usage_info.total_tokens
				elif isinstance(usage_info, dict):
					total_tokens = usage_info.get('total_tokens', input_tokens + output_tokens)
				else:
					total_tokens = input_tokens + output_tokens
			
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
					
					# Extract usage information from response
					if hasattr(response, 'usage'):
						usage_info = response.usage
					elif hasattr(response, 'response') and hasattr(response.response, 'usage'):
						usage_info = response.response.usage
					
					if usage_info:
						if hasattr(usage_info, 'input_tokens'):
							input_tokens = usage_info.input_tokens
						elif isinstance(usage_info, dict):
							input_tokens = usage_info.get('input_tokens', usage_info.get('prompt_tokens', 0))
						
						if hasattr(usage_info, 'output_tokens'):
							output_tokens = usage_info.output_tokens
						elif isinstance(usage_info, dict):
							output_tokens = usage_info.get('output_tokens', usage_info.get('completion_tokens', 0))
						
						if hasattr(usage_info, 'total_tokens'):
							total_tokens = usage_info.total_tokens
						elif isinstance(usage_info, dict):
							total_tokens = usage_info.get('total_tokens', input_tokens + output_tokens)
						else:
							total_tokens = input_tokens + output_tokens
				except APIError as api_err:
					print(f"{RESET_COLOR}Error: {api_err.message}{RESET_COLOR}")
					messages.pop()  # Remove the user message that failed
					continue
		
		# Calculate elapsed time
		elapsed_time = time.time() - start_time
		
		# Calculate cost
		cost = calculate_cost(MODEL, input_tokens, output_tokens) if total_tokens > 0 else None
		
		# Display statistics
		stats = format_statistics(input_tokens, output_tokens, total_tokens, cost, elapsed_time)
		if stats:
			console.print(f"[dim]{stats}[/dim]")
		
		print(RESET_COLOR, end="")

		messages.append({"role": "assistant", "content": full_response})
		
		# Save after receiving response
		if chat_name:
			save_conversation(chat_name, messages)
			# Update and save statistics
			update_statistics(chat_name, input_tokens, output_tokens, total_tokens, cost, elapsed_time)

if __name__ == "__main__":
	main()