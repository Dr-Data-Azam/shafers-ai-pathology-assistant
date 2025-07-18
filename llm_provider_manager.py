# File: llm_provider_manager.py
import os
from typing import List, Optional
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq

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
        raise Exception("No API keys found. Please set OPENAI_API_KEY or GROQ_API_KEY in your .env file")
    
    if provider not in available_providers:
        missing_key = "OPENAI_API_KEY" if provider == "openai" else "GROQ_API_KEY"
        raise Exception(f"Provider '{provider}' not available. Please set {missing_key} in your .env file")
    
    return True

def load_llm(provider: str = "openai"):
    """Load LLM based on provider choice"""
    global _llm_openai, _llm_groq
    
    # Validate provider first
    validate_provider(provider)
    
    if provider.lower() == "openai":
        if _llm_openai is not None:
            return _llm_openai
        
        try:
            _llm_openai = ChatOpenAI(
                model="gpt-4o",
                temperature=0.3,
                max_tokens=1500,
                timeout=60,
                request_timeout=60
            )
            return _llm_openai
        except Exception as e:
            raise Exception(f"Failed to load OpenAI model: {str(e)}")
    
    elif provider.lower() == "groq":
        if _llm_groq is not None:
            return _llm_groq
        
        try:
            _llm_groq = ChatGroq(
                model="llama-3.1-8b-instant",
                temperature=0.3,
                max_tokens=1500,
                timeout=60,
                request_timeout=60
            )
            return _llm_groq
        except Exception as e:
            raise Exception(f"Failed to load Groq model: {str(e)}")
    
    else:
        raise ValueError("Provider must be 'openai' or 'groq'")

def get_provider_info(provider: str) -> dict:
    """Get information about a specific provider"""
    provider_info = {
        "openai": {
            "name": "OpenAI GPT-4o",
            "speed": "Medium",
            "quality": "Excellent",
            "cost": "Higher",
            "description": "Most accurate and comprehensive responses"
        },
        "groq": {
            "name": "Groq Llama 3.1 70B",
            "speed": "Fast",
            "quality": "Very Good", 
            "cost": "Lower",
            "description": "Fast responses with good quality"
        }
    }
    
    return provider_info.get(provider.lower(), {})

def clear_llm_cache():
    """Clear cached LLM instances (useful for testing)"""
    global _llm_openai, _llm_groq
    _llm_openai = None
    _llm_groq = None