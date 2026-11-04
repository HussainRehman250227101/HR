class LLMConfigurationError(Exception):
    """Azure OpenAI is not configured correctly."""


class LLMProviderError(Exception):
    """The configured model provider could not complete a request."""


class LLMStructuredOutputError(LLMProviderError):
    """The model did not return a valid structured result."""
