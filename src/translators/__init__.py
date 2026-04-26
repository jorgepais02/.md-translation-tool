"""Translation providers package.

Public API — everything that was importable from translators.py is still importable here.
"""
from .base import BaseTranslator, TranslationError, FallbackTranslator, ProtectedTranslator
from .deepl import DeepLTranslator
from .azure import AzureTranslator
from .gemini import GeminiTranslator
from .wrappers import CachingTranslator
from .registry import AVAILABLE_TRANSLATORS, get_available_translators, get_translator

__all__ = [
    "BaseTranslator",
    "TranslationError",
    "FallbackTranslator",
    "ProtectedTranslator",
    "DeepLTranslator",
    "AzureTranslator",
    "GeminiTranslator",
    "CachingTranslator",
    "AVAILABLE_TRANSLATORS",
    "get_available_translators",
    "get_translator",
]

if __name__ == "__main__":
    import json
    from dotenv import load_dotenv
    load_dotenv()
    print(json.dumps(get_available_translators()))
