# File: chat_history_manager.py
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

CHAT_HISTORY_PATH = "chat_history.json"

def save_chat_history(question: str, answer: str, provider: str, 
                     retrieval_time: float, llm_time: float, total_time: float, 
                     pages_retrieved: int) -> bool:
    """Save chat interaction to history file"""
    try:
        # Load existing history
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
                "total_time": round(total_time, 2)
            },
            "pages_retrieved": pages_retrieved
        }
        
        history.append(interaction)
        
        # Keep only last 100 interactions to prevent file from getting too large
        if len(history) > 100:
            history = history[-100:]
        
        # Save updated history
        with open(CHAT_HISTORY_PATH, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        
        return True
            
    except Exception as e:
        print(f"Error saving chat history: {e}")
        return False

def load_chat_history() -> List[Dict[str, Any]]:
    """Load chat history from file"""
    try:
        if os.path.exists(CHAT_HISTORY_PATH):
            with open(CHAT_HISTORY_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        print(f"Error loading chat history: {e}")
        return []

def clear_chat_history() -> bool:
    """Clear all chat history"""
    try:
        if os.path.exists(CHAT_HISTORY_PATH):
            os.remove(CHAT_HISTORY_PATH)
        return True
    except Exception as e:
        print(f"Error clearing chat history: {e}")
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
            "most_recent": None
        }
    
    total_time = sum(interaction["performance"]["total_time"] for interaction in history)
    providers = list(set(interaction["provider"] for interaction in history))
    
    return {
        "total_interactions": len(history),
        "avg_response_time": round(total_time / len(history), 2),
        "providers_used": providers,
        "most_recent": history[-1]["timestamp"] if history else None
    }