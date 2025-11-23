#!/usr/bin/env python3
"""
Entry point for Textual-based UI for GPT CLI chat application.
"""

from ui import GptCliApp


def main():
	"""Main entry point for the UI application."""
	app = GptCliApp()
	app.run()


if __name__ == "__main__":
	main()

