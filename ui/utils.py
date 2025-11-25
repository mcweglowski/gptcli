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
		# Get last_used timestamp, fallback to file modification time if not set
		last_used = config.get("last_used")
		if last_used is None:
			# Use file modification time as fallback
			conv_path = gptcli.get_conversation_path(chat)
			if os.path.exists(conv_path):
				last_used = os.path.getmtime(conv_path)
			else:
				last_used = 0
		metadata.append({
			"name": chat,
			"model": model,
			"message_count": len(conversation),
			"last_used": last_used
		})
	# Sort by last_used descending (most recently used first)
	return sorted(metadata, key=lambda item: item["last_used"], reverse=True)


def format_chat_entry(chat):
	"""Format chat entry for display in list."""
	return chat["name"]

