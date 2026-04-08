import anthropic

from app.config import settings

_DEFAULT_MODEL = "claude-opus-4-6"
_DEFAULT_MAX_TOKENS = 2048


class AnthropicLLMClient:
    """
    Thin wrapper over the Anthropic Messages API.

    Centralises the model name, token budget, and SDK instantiation so
    nothing else in the codebase imports `anthropic` directly.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = _DEFAULT_MODEL,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
    ) -> None:
        self._client = anthropic.Anthropic(api_key=api_key or settings.anthropic_api_key)
        self.model = model
        self.max_tokens = max_tokens

    def complete(self, *, system: str, user: str) -> str:
        message = self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return message.content[0].text
