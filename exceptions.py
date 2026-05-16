class PathologyAppError(Exception):
    """Base exception for all Shafer's AI Pathology Assistant errors."""


class LLMError(PathologyAppError):
    """Raised when an LLM provider fails to load or generate a response."""

    def __init__(self, provider: str, message: str) -> None:
        self.provider = provider
        self.message = message
        super().__init__(f"[{provider}] {message}")


class RetrieverError(PathologyAppError):
    """Raised when the FAISS retriever fails to load or search."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ConfigError(PathologyAppError):
    """Raised when required configuration is missing or invalid."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)
