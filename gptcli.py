import argparse
import json
import os
from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown

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
	"""Loads conversation from file and returns the last 10 messages."""
	file_path = get_conversation_path(chat_name)
	if not os.path.exists(file_path):
		return []
	
	try:
		with open(file_path, 'r', encoding='utf-8') as f:
			messages = json.load(f)
		# Return the last 10 messages
		return messages[-10:] if len(messages) > 10 else messages
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

		messages.append({"role":"user", "content":user_input})
		
		# Save after adding user message
		if chat_name:
			save_conversation(chat_name, messages)

		# Use /v1/responses endpoint via OpenAI client's internal HTTP client
		response = client._client.post(
			"/v1/responses",
			json={
				"model": MODEL,
				"messages": messages
			}
		)
		response_data = response.json()
		message = response_data["choices"][0]["message"]["content"]
		print(f"{ASSISTANT_COLOR}GPT:")
		console.print(Markdown(message))
		print(RESET_COLOR, end="")

		messages.append({"role": "assistant", "content": message})
		
		# Save after receiving response
		if chat_name:
			save_conversation(chat_name, messages)

if __name__ == "__main__":
	main()