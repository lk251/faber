"""Optional OpenAI proof-planner adapter.

Importing this package never imports the optional OpenAI Python SDK. The SDK is loaded
only when a live backend constructs its default client.
"""

from faber.adapters.openai.prompt import (
    DEFAULT_MODEL,
    PROMPT_TEMPLATE_VERSION,
    RESPONSE_SCHEMA_VERSION,
)

__all__ = [
    "DEFAULT_MODEL",
    "PROMPT_TEMPLATE_VERSION",
    "RESPONSE_SCHEMA_VERSION",
]
