# File: chat_history_manager.py
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List

from config import get_config

logger = logging.getLogger(__name__)


def save_chat_history(
    question: str,
    answer: str,
    provider: str,
    retrieval_time: float,
    llm_time: float,
    total_time: float,
    pages_retrieved: int,
) -> bool:
    """Save chat interaction to history file"""
    try:
        history = load_chat_history()

        # Add new interaction
        interaction = {
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "answer": answer,
            "provider": provider.upper(),
            "performance": {
                "retrieval_time": round(retrieval_time, 2),
                "llm_time": round(llm_time, 2),
                "total_time": round(total_time, 2),
            },
            "pages_retrieved": pages_retrieved,
        }

        history.append(interaction)

        if len(history) > 100:
            history = history[-100:]

        with open(get_config().chat_history_path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

        return True

    except Exception as e:
        logger.error("Error saving chat history: %s", e)
        return False


def load_chat_history() -> List[Dict[str, Any]]:
    """Load chat history from file"""
    try:
        path = get_config().chat_history_path
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []
    except Exception as e:
        logger.error("Error loading chat history: %s", e)
        return []


def clear_chat_history() -> bool:
    """Clear all chat history"""
    try:
        path = get_config().chat_history_path
        if os.path.exists(path):
            os.remove(path)
        return True
    except Exception as e:
        logger.error("Error clearing chat history: %s", e)
        return False


def get_recent_history(limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent chat history with limit"""
    history = load_chat_history()
    return history[-limit:] if history else []


def get_history_stats() -> Dict[str, Any]:
    """Get statistics about chat history"""
    history = load_chat_history()

    if not history:
        return {
            "total_interactions": 0,
            "avg_response_time": 0,
            "providers_used": [],
            "most_recent": None,
        }

    total_time = sum(
        interaction["performance"]["total_time"] for interaction in history
    )
    providers = list(set(interaction["provider"] for interaction in history))

    return {
        "total_interactions": len(history),
        "avg_response_time": round(total_time / len(history), 2),
        "providers_used": providers,
        "most_recent": history[-1]["timestamp"] if history else None,
    }
