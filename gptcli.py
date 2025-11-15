from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown

client = OpenAI()
console = Console()

MODEL = "gpt-5.1"

USER_COLOR = "\033[96m"
ASSISTANT_COLOR = "\033[92m"
RESET_COLOR = "\033[0m"

def main():
	messages = []
	print("Console GPT chat. Type 'exit' or 'quit' to finish.")

	while True:
		user_input = input(f"{USER_COLOR}You: ")
		if user_input.lower() in ("exit", "quit"):
			break

		print(RESET_COLOR)

		messages.append({"role":"user", "content":user_input})

		response = client.chat.completions.create(
			model=MODEL,
			messages=messages
		)

		message = response.choices[0].message.content
		print(f"{ASSISTANT_COLOR}GPT:")
		console.print(Markdown(message))
		print(f"{RESET_COLOR}")

		messages.append({"role": "assistant", "content": message})

if __name__ == "__main__":
	main()