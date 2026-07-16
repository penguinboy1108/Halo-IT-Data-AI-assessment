"""Application-specific exceptions."""


class AgentError(Exception):
    """Base class for agent failures."""


class RefusalError(AgentError):
    """Raised when a request is intentionally refused."""


class SQLValidationError(AgentError):
    """Raised when SQL does not pass policy validation."""


class LLMError(AgentError):
    """Raised when an LLM call fails or returns invalid output."""
