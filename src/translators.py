import os
import sys
import requests
from abc import ABC, abstractmethod

# DeepL code → short filename code
LANG_MAP = {
    "EN-GB": "en",
    "FR":    "fr",
    "AR":    "ar",
    "ZH":    "zh",
}
DEFAULT_LANGS = list(LANG_MAP.keys())


class TranslationError(Exception):
    """Raised when a translation provider fails."""
    pass

class BaseTranslator(ABC):
    """Abstract base class for all translation providers."""
    
    @abstractmethod
    def translate(self, texts: list[str], target_lang: str) -> list[str]:
        """
        Translate a list of text strings.
        
        Args:
            texts: List of strings to translate.
            target_lang: The provider-specific language code.
            
        Returns:
            List of translated strings in the same order as `texts`.
        """
        pass

class DeepLTranslator(BaseTranslator):
    """Translator strategy using DeepL API."""
    
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("DEEPL_API_KEY", "")
        if not self.api_key:
            raise TranslationError("DEEPL_API_KEY not found in .env")
            
        # Keys ending in ":fx" belong to the free plan → api-free.deepl.com
        if self.api_key.endswith(":fx"):
            self.base_url = "https://api-free.deepl.com"
        else:
            self.base_url = "https://api.deepl.com"
            
        self.translate_url = f"{self.base_url}/v2/translate"
        self.max_batch_size = 50
        
    def translate(self, texts: list[str], target_lang: str) -> list[str]:
        if not texts:
            return []

        headers = {
            "Authorization": f"DeepL-Auth-Key {self.api_key}",
            "Content-Type": "application/json",
        }

        results: list[str] = []

        for i in range(0, len(texts), self.max_batch_size):
            chunk = texts[i : i + self.max_batch_size]
            payload = {
                "text": chunk,
                "target_lang": target_lang,
            }

            try:
                resp = requests.post(self.translate_url, json=payload, headers=headers, timeout=60)
                if resp.status_code == 456:
                    raise TranslationError("DeepL quota exceeded.")
                resp.raise_for_status()
                data = resp.json()

                for item in data["translations"]:
                    results.append(item["text"])
            except requests.exceptions.RequestException as e:
                raise TranslationError(f"DeepL API request failed: {e}") from e

        return results

class AzureTranslator(BaseTranslator):
    """Translator strategy using Azure AI Translator API."""
    
    def __init__(self, api_key: str | None = None, region: str | None = None):
        self.api_key = api_key or os.getenv("AZURE_TRANSLATOR_KEY", "")
        self.region = region or os.getenv("AZURE_TRANSLATOR_REGION", "")
        
        if not self.api_key:
            raise TranslationError("AZURE_TRANSLATOR_KEY not found in .env")
            
        # Text Translation API v3.0
        self.base_url = "https://api.cognitive.microsofttranslator.com"
        self.translate_url = f"{self.base_url}/translate"
        self.max_batch_size = 100 # Azure text translation allows up to 100 array elements
        
    def _map_lang_code(self, lang: str) -> str:
        """Map standard/DeepL lang codes to Azure lang codes if needed."""
        # Azure uses standard BCP 47. 
        # DeepL EN-GB -> Azure en-GB
        if lang.upper() == "EN-GB":
            return "en-GB"
        # Others like FR, AR, ZH -> fr, ar, zh-Hans (typically)
        if lang.upper() == "ZH":
            return "zh-Hans" # Defaulting to simplified Chinese
        return lang.lower()
        
    def translate(self, texts: list[str], target_lang: str) -> list[str]:
        if not texts:
            return []

        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
            "Content-type": "application/json",
        }
        if self.region:
            headers["Ocp-Apim-Subscription-Region"] = self.region

        results: list[str] = []
        azure_target_lang = self._map_lang_code(target_lang)
        
        params = {
            "api-version": "3.0",
            "to": [azure_target_lang]
        }

        # Azure requires [{"text": "sentence1"}, {"text": "sentence2"}]
        for i in range(0, len(texts), self.max_batch_size):
            chunk = texts[i : i + self.max_batch_size]
            payload = [{"text": text} for text in chunk]

            try:
                resp = requests.post(self.translate_url, params=params, json=payload, headers=headers, timeout=60)
                if resp.status_code == 403:
                    msg = f"Azure API Error ({resp.status_code}). Check your tier quota or valid region."
                    if "out of call volume quota" in resp.text.lower():
                        msg += " Quota exceeded."
                    raise TranslationError(msg)
                resp.raise_for_status()
                data = resp.json()

                for item in data:
                    results.append(item["translations"][0]["text"])
            except requests.exceptions.RequestException as e:
                detail = ""
                if hasattr(e, 'response') and e.response is not None and hasattr(e.response, 'text'):
                    detail = f" — {e.response.text}"
                raise TranslationError(f"Azure API request failed: {e}{detail}") from e

        return results


class FallbackTranslator(BaseTranslator):
    """Translator that tries multiple providers in order, falling back on failure."""

    def __init__(self, translators: list[BaseTranslator]):
        if not translators:
            raise ValueError("FallbackTranslator requires at least one translator.")
        self.translators = translators

    def translate(self, texts: list[str], target_lang: str) -> list[str]:
        errors: list[str] = []
        for t in self.translators:
            try:
                return t.translate(texts, target_lang)
            except TranslationError as e:
                name = type(t).__name__
                print(f"  ⚠ {name} failed: {e}  — trying next provider…", file=sys.stderr)
                errors.append(f"{name}: {e}")
        raise TranslationError(
            "All translation providers failed:\n  " + "\n  ".join(errors)
        )


def get_translator(provider: str) -> BaseTranslator:
    """Factory to return the correctly configured translator.

    If *provider* is ``'auto'``, builds a :class:`FallbackTranslator` using
    every provider whose API key is present in the environment (DeepL first,
    then Azure).  Falls back gracefully when only one key is available.
    """
    provider = provider.lower()

    if provider == "auto":
        translators: list[BaseTranslator] = []
        # Try DeepL first
        if os.getenv("DEEPL_API_KEY", ""):
            try:
                translators.append(DeepLTranslator())
            except TranslationError:
                pass
        # Then Azure
        if os.getenv("AZURE_TRANSLATOR_KEY", ""):
            try:
                translators.append(AzureTranslator())
            except TranslationError:
                pass
        if not translators:
            raise TranslationError(
                "No translation provider configured. "
                "Set DEEPL_API_KEY or AZURE_TRANSLATOR_KEY in your .env file."
            )
        if len(translators) == 1:
            return translators[0]
        return FallbackTranslator(translators)

    if provider == "deepl":
        return DeepLTranslator()
    elif provider == "azure":
        return AzureTranslator()
    else:
        raise ValueError(f"Unknown translation provider: {provider}")
