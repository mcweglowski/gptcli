#!/usr/bin/env python3
"""
Utility functions for UI.
"""

import os
import gptcli


def get_available_chats():
	"""Get list of available chats with metadata."""
	if not os.path.exists(gptcli.CONVERSATIONS_DIR):
		return []
	chats = []
	for entry in os.listdir(gptcli.CONVERSATIONS_DIR):
		full_path = os.path.join(gptcli.CONVERSATIONS_DIR, entry)
		if os.path.isdir(full_path):
			continue
		if entry.endswith(".config.json"):
			continue
		if entry.endswith(".json"):
			chats.append(entry[:-5])
	metadata = []
	for chat in chats:
		config = gptcli.load_chat_config(chat)
		model = config.get("model", gptcli.DEFAULT_MODEL)
		conversation = gptcli.load_conversation(chat)
		metadata.append({
			"name": chat,
			"model": model,
			"message_count": len(conversation)
		})
	return sorted(metadata, key=lambda item: item["name"])


def format_chat_entry(chat):
	"""Format chat entry for display in list."""
	return chat["name"]

