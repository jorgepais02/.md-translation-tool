from .base import BaseTranslator, FallbackTranslator, ProtectedTranslator, TranslationError
from .deepl import DeepLTranslator
from .azure import AzureTranslator
from .gemini import GeminiTranslator
from .wrappers import CachingTranslator
from .cache import TranslationCache


AVAILABLE_TRANSLATORS: dict[str, tuple[str, type[BaseTranslator]]] = {
    "deepl":  ("DeepL API", DeepLTranslator),
    "azure":  ("Azure AI Translator", AzureTranslator),
    "gemini": ("Gemini (Google AI)", GeminiTranslator),
}


def get_available_translators() -> list[dict]:
    """Return translators whose API key is present in the environment."""
    available = []
    for key, (name, cls) in AVAILABLE_TRANSLATORS.items():
        try:
            cls()
            available.append({"id": key, "name": name})
        except TranslationError:
            pass
    return available


def get_translator(fallback_order: list[str] | str) -> BaseTranslator:
    """Factory that returns a ProtectedTranslator wrapping a FallbackTranslator.

    Args:
        fallback_order: Provider IDs in priority order, or 'auto' to use all available.
    """
    if isinstance(fallback_order, str):
        fallback_order = [fallback_order]

    if not fallback_order or fallback_order[0].lower() == "auto":
        fallback_order = list(AVAILABLE_TRANSLATORS.keys())

    cache = TranslationCache()
    translators: list[BaseTranslator] = []

    for provider_id in fallback_order:
        provider_id = provider_id.lower()
        if provider_id in AVAILABLE_TRANSLATORS:
            _, cls = AVAILABLE_TRANSLATORS[provider_id]
            try:
                translators.append(CachingTranslator(cls(), cache))
            except TranslationError as e:
                if provider_id == fallback_order[0].lower():
                    raise TranslationError(f"Failed to initialize requested provider '{provider_id}': {e}")

    # Append any available providers not explicitly requested
    seen = {type(t.translator) for t in translators if isinstance(t, CachingTranslator)}
    for provider_id, (_, cls) in AVAILABLE_TRANSLATORS.items():
        if provider_id not in [p.lower() for p in fallback_order] and cls not in seen:
            try:
                translators.append(CachingTranslator(cls(), cache))
            except TranslationError:
                pass

    if not translators:
        raise TranslationError(
            "No translation provider configured. "
            "Please add an API key (e.g. DEEPL_API_KEY) to your .env file."
        )

    result = translators[0] if len(translators) == 1 else FallbackTranslator(translators)
    return ProtectedTranslator(result)
