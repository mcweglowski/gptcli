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
		# Use file modification time for sorting
		conv_path = gptcli.get_conversation_path(chat)
		if os.path.exists(conv_path):
			last_modified = os.path.getmtime(conv_path)
		else:
			last_modified = 0
		metadata.append({
			"name": chat,
			"model": model,
			"message_count": len(conversation),
			"last_modified": last_modified
		})
	# Sort by last_modified descending (most recently modified first)
	return sorted(metadata, key=lambda item: item["last_modified"], reverse=True)


def format_chat_entry(chat):
	"""Format chat entry for display in list."""
	return chat["name"]

