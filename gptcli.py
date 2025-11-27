import argparse
import gnureadline as readline
import json

# Disable history and autocompletion, but keep basic editing (arrows, copy/paste)
readline.set_history_length(0)  # Disable history
readline.set_auto_history(False)  # Don't add to history
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
INFO_COLOR = "\033[95m"
RESET_COLOR = "\033[0m"

CONVERSATIONS_DIR = "conversations"
CONFIG_PATH = os.environ.get("GPTCLI_CONFIG_PATH", "config.json")

DEFAULT_CONFIG = {
	"default_model": "gpt-5.1",
	"user_name": "You",
	"user_color": "cyan",
	"assistant_color": "green",
	"pricing": {
		"gpt-5.1": {"input": 2.50, "output": 10.00}
	},
	"system_prompts": {
		"default": "You are a helpful assistant.",
		"python-expert": "You are an expert Python programmer. Provide technical, concise answers with code examples.",
		"friendly-mentor": "You are a friendly mentor. Use simple language, give practical advice, and be encouraging.",
		"data-analyst": "You are a data analysis assistant. Always format responses as structured reports with sections."
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
		if isinstance(data.get("user_name"), str):
			config["user_name"] = data["user_name"]
		if isinstance(data.get("user_color"), str):
			config["user_color"] = data["user_color"]
		if isinstance(data.get("assistant_color"), str):
			config["assistant_color"] = data["assistant_color"]
		if isinstance(data.get("system_prompts"), dict):
			config["system_prompts"].update(data["system_prompts"])
	return config


CONFIG = load_config()
DEFAULT_MODEL = CONFIG.get("default_model", DEFAULT_CONFIG["default_model"])
USER_NAME = CONFIG.get("user_name", DEFAULT_CONFIG["user_name"])
USER_COLOR = CONFIG.get("user_color", DEFAULT_CONFIG["user_color"])
ASSISTANT_COLOR = CONFIG.get("assistant_color", DEFAULT_CONFIG["assistant_color"])
MODEL_PRICING = CONFIG.get("pricing", DEFAULT_CONFIG["pricing"])
SYSTEM_PROMPTS = CONFIG.get("system_prompts", DEFAULT_CONFIG["system_prompts"])


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


def get_chat_config_path(chat_name):
	"""Returns the path to per-chat configuration."""
	if not os.path.exists(CONVERSATIONS_DIR):
		os.makedirs(CONVERSATIONS_DIR)
	return os.path.join(CONVERSATIONS_DIR, f"{chat_name}.config.json")


def get_system_prompt_path(chat_name):
	"""Returns the path to the custom system prompt file."""
	if not os.path.exists(CONVERSATIONS_DIR):
		os.makedirs(CONVERSATIONS_DIR)
	system_prompts_dir = os.path.join(CONVERSATIONS_DIR, "system_prompts")
	if not os.path.exists(system_prompts_dir):
		os.makedirs(system_prompts_dir)
	return os.path.join(system_prompts_dir, f"{chat_name}.json")


def save_system_prompt(chat_name, prompt):
	"""Saves (or removes) the custom system prompt for a chat."""
	file_path = get_system_prompt_path(chat_name)
	if not prompt:
		if os.path.exists(file_path):
			try:
				os.remove(file_path)
			except OSError:
				print(f"{RESET_COLOR}Warning: Could not remove system prompt file {file_path}")
		return
	try:
		with open(file_path, "w", encoding="utf-8") as f:
			json.dump({"system_prompt": prompt}, f, ensure_ascii=False, indent=2)
	except IOError:
		print(f"{RESET_COLOR}Warning: Could not save system prompt to {file_path}")


def load_chat_config(chat_name):
	"""Loads per-chat configuration."""
	file_path = get_chat_config_path(chat_name)
	if not os.path.exists(file_path):
		return {}
	try:
		with open(file_path, "r", encoding="utf-8") as f:
			data = json.load(f)
			return data if isinstance(data, dict) else {}
	except (json.JSONDecodeError, IOError):
		return {}


def save_chat_config(chat_name, config):
	"""Saves per-chat configuration."""
	file_path = get_chat_config_path(chat_name)
	try:
		with open(file_path, "w", encoding="utf-8") as f:
			json.dump(config, f, ensure_ascii=False, indent=2)
	except IOError:
		print(f"{RESET_COLOR}Warning: Could not save chat config to {file_path}")


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
	parser.add_argument('--chat-name', '-n', type=str, help='Chat name (optional)')
	parser.add_argument('--model', type=str, help='Override model for this chat session')
	parser.add_argument('--list-chats', action='store_true', help='List available chats and exit')
	args = parser.parse_args()

	def get_available_chats():
		if not os.path.exists(CONVERSATIONS_DIR):
			return []
		chats = []
		for entry in os.listdir(CONVERSATIONS_DIR):
			full_path = os.path.join(CONVERSATIONS_DIR, entry)
			if os.path.isdir(full_path):
				continue
			if entry.endswith(".config.json"):
				continue
			if entry.endswith(".json"):
				chats.append(entry[:-5])
		metadata = []
		for chat in chats:
			config = load_chat_config(chat)
			model = config.get("model", DEFAULT_MODEL)
			conversation = load_conversation(chat)
			metadata.append({
				"name": chat,
				"model": model,
				"message_count": len(conversation)
			})
		return sorted(metadata, key=lambda item: item["name"])

	def format_chat_entry(chat):
		name = chat["name"] if len(chat["name"]) <= 24 else chat["name"][:21] + "..."
		model = chat["model"]
		return f"{name:<24} | {model:<16} | messages: {chat['message_count']:>5}"

	if args.list_chats:
		chats = get_available_chats()
		if chats:
			print(f"{INFO_COLOR}Available chats:{RESET_COLOR}")
			for chat in chats:
				print(f"{INFO_COLOR} - {format_chat_entry(chat)}{RESET_COLOR}")
		else:
			print(f"{INFO_COLOR}No conversations found.{RESET_COLOR}")
		return
	
	chat_name = args.chat_name
	messages = []
	chat_config = {}
	if chat_name:
		chat_config = load_chat_config(chat_name)
	
	current_model = DEFAULT_MODEL
	if args.model:
		current_model = args.model
		if chat_name:
			chat_config["model"] = current_model
			save_chat_config(chat_name, chat_config)
	elif chat_config.get("model"):
		current_model = chat_config["model"]
	
	current_system_prompt = None
	if chat_config.get("system_prompt"):
		prompt_name = chat_config["system_prompt"]
		if prompt_name in SYSTEM_PROMPTS:
			current_system_prompt = SYSTEM_PROMPTS[prompt_name]
		else:
			# If prompt name not found, use it as direct text
			current_system_prompt = prompt_name
	
	def announce_chat():
		if chat_name:
			info = f"{INFO_COLOR}Chat: {chat_name}"
			print(f"{info}{RESET_COLOR}")
			if messages:
				print(f"{ASSISTANT_COLOR}Loaded conversation: {chat_name} ({len(messages)} messages){RESET_COLOR}")
			else:
				print(f"{ASSISTANT_COLOR}Starting new conversation: {chat_name}{RESET_COLOR}")
		else:
			print(f"{INFO_COLOR}Console GPT chat (temporary conversation - not saved). Type 'quit' to finish.{RESET_COLOR}")
		print(f"{ASSISTANT_COLOR}Using model: {current_model}{RESET_COLOR}")
		if current_system_prompt:
			prompt_display = current_system_prompt[:50] + "..." if len(current_system_prompt) > 50 else current_system_prompt
			print(f"{ASSISTANT_COLOR}System prompt: {prompt_display}{RESET_COLOR}")

	def print_info(message):
		print(f"{INFO_COLOR}{message}{RESET_COLOR}")

	def load_chat(new_chat_name):
		nonlocal chat_name, chat_config, messages, current_model, current_system_prompt
		chat_name = new_chat_name
		messages.clear()
		chat_config = {}
		if chat_name:
			chat_config = load_chat_config(chat_name)
			messages.extend(load_conversation(chat_name))
			if chat_config.get("model"):
				current_model = chat_config["model"]
			else:
				current_model = DEFAULT_MODEL
			
			current_system_prompt = None
			if chat_config.get("system_prompt"):
				prompt_name = chat_config["system_prompt"]
				if prompt_name in SYSTEM_PROMPTS:
					current_system_prompt = SYSTEM_PROMPTS[prompt_name]
				else:
					current_system_prompt = prompt_name
		else:
			current_model = DEFAULT_MODEL
			current_system_prompt = None
		announce_chat()

	if chat_name:
		load_chat(chat_name)
		if args.model:
			current_model = args.model
			chat_config["model"] = current_model
			save_chat_config(chat_name, chat_config)
			print_info(f"Model for chat '{chat_name}' set to {current_model}.")
	else:
		announce_chat()

	def handle_command(command_line):
		nonlocal current_model, current_system_prompt
		stripped = command_line[1:].strip()
		if not stripped:
			print_info("Empty command.")
			return True, False
		parts = stripped.split()
		command = parts[0].lower()
		args_list = parts[1:]

		if command == "quit":
			return True, True

		if command == "help":
			print_info("Available commands:")
			print_info(" /help                - show this help")
			print_info(" /change-model <name> - change model for current chat/session")
			print_info(" /system-prompt <name> - set system prompt for current chat")
			print_info(" /system-prompt-list  - list available system prompts")
			print_info(" /list-chats          - list available chats")
			print_info(" /switch-chat <name>  - switch to another chat")
			print_info(" /quit                - exit the application")
			return True, False

		if command == "change-model":
			if not args_list:
				print_info("Usage: /change-model <model_name>")
				return True, False
			new_model = args_list[0]
			current_model = new_model
			if chat_name:
				chat_config["model"] = new_model
				save_chat_config(chat_name, chat_config)
				print_info(f"Model for chat '{chat_name}' set to {new_model}.")
			else:
				print_info(f"Using model {new_model} for temporary conversation.")
			return True, False

		if command == "list-chats":
			chats = get_available_chats()
			if chats:
				print_info("Available chats:")
				for chat in chats:
					print_info(f" - {format_chat_entry(chat)}")
			else:
				print_info("No conversations found.")
			return True, False

		if command == "switch-chat":
			if not args_list:
				print_info("Usage: /switch-chat <chat_name>")
				return True, False
			target = args_list[0]
			load_chat(target)
			return True, False

		if command == "system-prompt":
			if not args_list:
				print_info("Usage: /system-prompt <prompt_name>")
				print_info("Use /system-prompt-list to see available prompts")
				return True, False
			prompt_name = args_list[0]
			if prompt_name in SYSTEM_PROMPTS:
				current_system_prompt = SYSTEM_PROMPTS[prompt_name]
				if chat_name:
					chat_config["system_prompt"] = prompt_name
					save_chat_config(chat_name, chat_config)
					print_info(f"System prompt for chat '{chat_name}' set to '{prompt_name}'.")
				else:
					print_info(f"Using system prompt '{prompt_name}' for temporary conversation.")
			else:
				# Allow direct text as system prompt
				current_system_prompt = " ".join(args_list)
				if chat_name:
					chat_config["system_prompt"] = current_system_prompt
					save_chat_config(chat_name, chat_config)
					print_info(f"System prompt for chat '{chat_name}' set to custom text.")
				else:
					print_info(f"Using custom system prompt for temporary conversation.")
			return True, False

		if command == "system-prompt-list":
			print_info("Available system prompts:")
			for name, prompt in SYSTEM_PROMPTS.items():
				preview = prompt[:60] + "..." if len(prompt) > 60 else prompt
				print_info(f"  {name:<20} - {preview}")
			return True, False

		print_info(f"Unknown command: /{command}")
		return True, False
	
	while True:
		user_input = input(f"{USER_COLOR}You: ")
		if user_input.startswith("/"):
			handled, should_exit = handle_command(user_input)
			if should_exit:
				break
			if handled:
				continue
		if user_input.lower() in ("exit", "quit"):
			break

		print(RESET_COLOR)

		messages.append({"role": "user", "content":user_input})

		# Use only last 10 messages for API to avoid token limits
		api_messages = messages[-10:] if len(messages) > 10 else messages.copy()
		# Remove 'model' and 'timestamp' fields from messages before sending to API
		api_messages = [{k: v for k, v in msg.items() if k not in ("model", "timestamp")} for msg in api_messages]
		
		# Add system prompt if set (only if not already in messages)
		if current_system_prompt:
			# Check if first message is already a system prompt
			if not api_messages or api_messages[0].get("role") != "system":
				api_messages = [{"role": "system", "content": current_system_prompt}] + api_messages
			else:
				# Update existing system prompt
				api_messages[0]["content"] = current_system_prompt

		# Try streaming first, fallback to regular if not supported
		full_response = ""
		header_chat = chat_name if chat_name else "temp"
		print(f"{ASSISTANT_COLOR}GPT({header_chat}|{current_model}): {RESET_COLOR}")
		
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
					model=current_model,
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
						model=current_model,
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
		cost = calculate_cost(current_model, input_tokens, output_tokens) if total_tokens > 0 else None
		
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