from openai import OpenAI

client = OpenAI()

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

		stream = client.chat.completions.create(
			model=MODEL,
			messages=messages,
			stream=True
		)

		message = ""
		print(f"{ASSISTANT_COLOR}GPT: ")

		for chunk in stream:
			if chunk.choices[0].delta.content:
				print(chunk.choices[0].delta.content, end="", flush=True)
				message += chunk.choices[0].delta.content


		messages.append({"role": "assistant", "content": message})
		print(RESET_COLOR)

if __name__ == "__main__":
	main()