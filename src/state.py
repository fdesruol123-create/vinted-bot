import json
import os
import logging
from typing import Set

STATE_FILE = os.environ.get("STATE_FILE", "data/state.json")

logger = logging.getLogger(__name__)


def _load() -> dict:
    if not os.path.exists(STATE_FILE):
        return {"messaged_likers": [], "replied_conversations": []}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_messaged_likers() -> Set[str]:
    return set(_load().get("messaged_likers", []))


def get_replied_conversations() -> Set[int]:
    return set(_load().get("replied_conversations", []))


def mark_liker_messaged(user_id: int, item_id: int) -> None:
    data = _load()
    key = f"{user_id}_{item_id}"
    if key not in data["messaged_likers"]:
        data["messaged_likers"].append(key)
        _save(data)
        logger.debug(f"Liker marqué comme contacté : user={user_id} item={item_id}")


def mark_conversation_replied(conv_id: int) -> None:
    data = _load()
    if conv_id not in data["replied_conversations"]:
        data["replied_conversations"].append(conv_id)
        _save(data)
        logger.debug(f"Conversation marquée comme répondue : {conv_id}")


def is_liker_messaged(user_id: int, item_id: int) -> bool:
    return f"{user_id}_{item_id}" in get_messaged_likers()


def is_conversation_replied(conv_id: int) -> bool:
    return conv_id in get_replied_conversations()
