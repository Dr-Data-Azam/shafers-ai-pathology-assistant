# File: llm_provider_manager.py
import logging
import os
from typing import List, Union

from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

from config import get_config
from exceptions import LLMError

logger = logging.getLogger(__name__)

# Global cache for LLM instances
_llm_openai = None
_llm_groq = None


def get_available_providers() -> List[str]:
    """Check which providers are available based on API keys"""
    providers = []

    # Check OpenAI
    if os.getenv("OPENAI_API_KEY"):
        providers.append("openai")

    # Check Groq
    if os.getenv("GROQ_API_KEY"):
        providers.append("groq")

    return providers


def validate_provider(provider: str) -> bool:
    """Validate if the provider is available"""
    available_providers = get_available_providers()

    if not available_providers:
        msg = "No API keys found. Please set OPENAI_API_KEY or GROQ_API_KEY in your .env file"
        logger.error(msg)
        raise LLMError(provider=provider, message=msg)

    if provider not in available_providers:
        missing_key = "OPENAI_API_KEY" if provider == "openai" else "GROQ_API_KEY"
        msg = f"Provider '{provider}' not available. Please set {missing_key} in your .env file"
        logger.error(msg)
        raise LLMError(provider=provider, message=msg)

    return True


def load_llm(provider: str = "openai") -> Union[ChatOpenAI, ChatGroq]:
    """Load LLM based on provider choice"""
    global _llm_openai, _llm_groq

    validate_provider(provider)

    cfg = get_config()

    if provider.lower() == "openai":
        if _llm_openai is not None:
            return _llm_openai

        try:
            _llm_openai = ChatOpenAI(
                model=cfg.openai_model,
                temperature=cfg.temperature,
                max_tokens=cfg.max_tokens,
                timeout=cfg.llm_timeout,
                request_timeout=cfg.llm_timeout,
            )
            return _llm_openai
        except Exception as e:
            safe_msg = getattr(e, "message", None) or type(e).__name__
            logger.error("Failed to load OpenAI model: %s", safe_msg)
            raise LLMError(provider="openai", message=safe_msg)

    elif provider.lower() == "groq":
        if _llm_groq is not None:
            return _llm_groq

        try:
            _llm_groq = ChatGroq(
                model=cfg.groq_model,
                temperature=cfg.temperature,
                max_tokens=cfg.max_tokens,
                timeout=cfg.llm_timeout,
                request_timeout=cfg.llm_timeout,
            )
            return _llm_groq
        except Exception as e:
            safe_msg = getattr(e, "message", None) or type(e).__name__
            logger.error("Failed to load Groq model: %s", safe_msg)
            raise LLMError(provider="groq", message=safe_msg)

    else:
        msg = f"Unknown provider '{provider}'. Must be 'openai' or 'groq'."
        logger.error(msg)
        raise LLMError(provider=provider, message=msg)


def get_provider_info(provider: str) -> dict:
    """Get information about a specific provider"""
    provider_info = {
        "openai": {
            "name": "OpenAI GPT-4o",
            "speed": "Medium",
            "quality": "Excellent",
            "cost": "Higher",
            "description": "Most accurate and comprehensive responses",
        },
        "groq": {
            "name": "Groq Llama 3.1 70B",
            "speed": "Fast",
            "quality": "Very Good",
            "cost": "Lower",
            "description": "Fast responses with good quality",
        },
    }

    return provider_info.get(provider.lower(), {})


def clear_llm_cache() -> None:
    """Clear cached LLM instances (useful for testing)"""
    global _llm_openai, _llm_groq
    _llm_openai = None
    _llm_groq = None
