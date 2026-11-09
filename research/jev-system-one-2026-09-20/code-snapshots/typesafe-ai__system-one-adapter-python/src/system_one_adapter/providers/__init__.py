"""Provider seam: OpenAI-compatible and native Anthropic model requests.

The concrete providers live in `system_one_adapter.providers.openai` and
`system_one_adapter.providers.anthropic` and each needs its own optional dependency
(the `openai` / `anthropic` extras). They are imported lazily, only when selected,
so importing this package needs neither SDK installed.
"""

from system_one_adapter.providers.base import (
    AsyncProvider,
    Message,
    ProviderName,
    ProviderResult,
    SyncProvider,
    capture_attempt,
    translating,
)

__all__ = [
    "AsyncProvider",
    "Message",
    "ProviderName",
    "ProviderResult",
    "SyncProvider",
    "build_async_provider",
    "build_sync_provider",
    "capture_attempt",
    "translating",
]

_MISSING_PROVIDER = "A provider is required: set provider='openai' or 'anthropic', or pass a provider instance as the model."


def _missing_extra(provider: str) -> ValueError:
    return ValueError(
        f"The {provider!r} provider requires its optional dependency; install it with: pip install 'system-one-adapter[{provider}]'"
    )


def build_sync_provider(
    provider: ProviderName | None,
    model: str | SyncProvider,
) -> SyncProvider:
    """Build the selected synchronous provider, or use an injected provider.

    Args:
        provider: `"openai"` or `"anthropic"`, or `None` when `model` is
            already a provider instance.
        model: Model name for the selected provider, or a ready `SyncProvider`
            such as a custom OpenAI-compatible endpoint or test double.

    Returns:
        A new synchronous provider, or the supplied instance unchanged.

    Raises:
        ValueError: A model name has no provider selector, or the selected
            provider's optional dependency is missing.
    """
    if not isinstance(model, str):
        return model
    if provider is None:
        raise ValueError(_MISSING_PROVIDER)
    if provider == "openai":
        try:
            from system_one_adapter.providers.openai import OpenAIProvider  # noqa: PLC0415
        except ImportError as error:
            raise _missing_extra("openai") from error
        return OpenAIProvider(model)
    try:
        from system_one_adapter.providers.anthropic import AnthropicProvider  # noqa: PLC0415
    except ImportError as error:
        raise _missing_extra("anthropic") from error
    return AnthropicProvider(model)


def build_async_provider(
    provider: ProviderName | None,
    model: str | AsyncProvider,
) -> AsyncProvider:
    """Build the selected asynchronous provider, or use an injected provider.

    Args:
        provider: `"openai"` or `"anthropic"`, or `None` when `model` is
            already a provider instance.
        model: Model name for the selected provider, or a ready `AsyncProvider`
            such as a custom OpenAI-compatible endpoint or test double.

    Returns:
        A new asynchronous provider, or the supplied instance unchanged.

    Raises:
        ValueError: A model name has no provider selector, or the selected
            provider's optional dependency is missing.
    """
    if not isinstance(model, str):
        return model
    if provider is None:
        raise ValueError(_MISSING_PROVIDER)
    if provider == "openai":
        try:
            from system_one_adapter.providers.openai import AsyncOpenAIProvider  # noqa: PLC0415
        except ImportError as error:
            raise _missing_extra("openai") from error
        return AsyncOpenAIProvider(model)
    try:
        from system_one_adapter.providers.anthropic import AsyncAnthropicProvider  # noqa: PLC0415
    except ImportError as error:
        raise _missing_extra("anthropic") from error
    return AsyncAnthropicProvider(model)
