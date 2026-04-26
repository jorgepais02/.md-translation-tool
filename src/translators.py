import os
import sys
import re as _re
import requests
from abc import ABC, abstractmethod
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from translation_cache import TranslationCache

_INLINE_CODE_RE    = _re.compile(r'`[^`\n]+`')
_FORMULA_BLOCK_RE  = _re.compile(r'\$\$[\s\S]+?\$\$')
_FORMULA_INLINE_RE = _re.compile(r'\$[^$\n]+\$')
_URL_RE            = _re.compile(r'https?://\S+')

def _protect_tokens(text: str) -> tuple[str, list[str]]:
    tokens: list[str] = []
    def _replace(m: _re.Match) -> str:
        tokens.append(m.group(0))
        return f"⟦{len(tokens)-1}⟧"
    out = _FORMULA_BLOCK_RE.sub(_replace, text)
    out = _FORMULA_INLINE_RE.sub(_replace, out)
    out = _INLINE_CODE_RE.sub(_replace, out)
    out = _URL_RE.sub(_replace, out)
    return out, tokens

def _restore_tokens(text: str, tokens: list[str]) -> str:
    for i, tok in enumerate(tokens):
        text = text.replace(f"⟦{i}⟧", tok)
    return text

# Legacy language mappings removed in favor of config.json


class TranslationError(Exception):
    """Raised when a translation provider fails."""
    pass

class BaseTranslator(ABC):
    """Abstract base class for all translation providers."""

    name: str = "unknown"

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

    name = "deepl"

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

    name = "azure"

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
                errors.append(f"{type(t).__name__}: {e}")
        raise TranslationError(
            "All translation providers failed:\n  " + "\n  ".join(errors)
        )


class GeminiTranslator(BaseTranslator):
    """Translator using Gemini (gemini-2.5-flash) with a technical translation prompt."""

    name = "gemini"
    _LANG_NAMES = {
        "EN": "English", "FR": "French", "AR": "Arabic", "ZH": "Chinese (Simplified)",
        "DE": "German", "IT": "Italian", "PT": "Portuguese", "RU": "Russian",
        "JA": "Japanese", "KO": "Korean", "HE": "Hebrew", "FA": "Persian",
        "UR": "Urdu", "ES": "Spanish", "NL": "Dutch", "PL": "Polish",
    }
    _PROMPT_TMPL = (
        "You are a professional technical translator specialized in cybersecurity and computer science.\n"
        "Translate each line of the following numbered list to {lang_name}.\n"
        "Rules:\n"
        "- Return ONLY the translated lines, one per line, same count as input\n"
        "- Preserve Markdown formatting\n"
        "- Do NOT translate inline code spans (text between backticks)\n"
        "- Do NOT translate acronyms like API, RSA, SQL, HTTP, DNS, IP\n"
        "- Use correct cybersecurity terminology natural in {lang_name}\n"
        "- No explanations, no extra text\n\n"
        "Lines to translate:\n{numbered}"
    )
    max_batch_size = 30

    def __init__(self, api_key: str | None = None):
        from google import genai
        from google.genai import types as _types
        self._api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        if not self._api_key:
            raise TranslationError("GEMINI_API_KEY not found in .env")
        self._client = genai.Client(api_key=self._api_key)
        self._types = _types

    def translate(self, texts: list[str], target_lang: str) -> list[str]:
        if not texts:
            return []
        lang_key = target_lang.upper().split("-")[0]
        lang_name = self._LANG_NAMES.get(lang_key, target_lang)
        results: list[str] = []
        for i in range(0, len(texts), self.max_batch_size):
            chunk = texts[i: i + self.max_batch_size]
            numbered = "\n".join(f"{j+1}. {t}" for j, t in enumerate(chunk))
            prompt = self._PROMPT_TMPL.format(lang_name=lang_name, numbered=numbered)
            try:
                response = self._client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                )
                lines = [l.strip() for l in response.text.strip().splitlines() if l.strip()]
                cleaned = []
                for idx, line in enumerate(lines):
                    if line.startswith(f"{idx+1}. "):
                        cleaned.append(line[len(f"{idx+1}. "):])
                    elif line.startswith(f"{idx+1}."):
                        cleaned.append(line[len(f"{idx+1}."):].lstrip())
                    else:
                        cleaned.append(line)
                if len(cleaned) != len(chunk):
                    raise TranslationError(
                        f"Gemini returned {len(cleaned)} lines for {len(chunk)} inputs"
                    )
                results.extend(cleaned)
            except TranslationError:
                raise
            except Exception as e:
                raise TranslationError(f"Gemini API request failed: {e}") from e
        return results


class CachingTranslator(BaseTranslator):
    """Transparent cache wrapper around any BaseTranslator.

    Checks cache before calling the underlying API. Only missed texts
    are sent to the provider; results are stored for future runs.
    """

    def __init__(self, translator: BaseTranslator, cache: TranslationCache):
        self.translator = translator
        self.cache      = cache
        self.name       = translator.name

    def translate(self, texts: list[str], target_lang: str) -> list[str]:
        results: list[str | None] = []
        miss_idx:   list[int] = []
        miss_texts: list[str] = []

        for i, text in enumerate(texts):
            cached = self.cache.get(text, target_lang, self.name)
            if cached is not None:
                results.append(cached)
            else:
                results.append(None)
                miss_idx.append(i)
                miss_texts.append(text)

        if miss_texts:
            translated = self.translator.translate(miss_texts, target_lang)
            for idx, src, tgt in zip(miss_idx, miss_texts, translated):
                self.cache.set(src, target_lang, self.name, tgt)
                results[idx] = tgt

        return results  # type: ignore[return-value]


class ProtectedTranslator(BaseTranslator):
    """Wraps any translator to protect inline code spans and URLs from translation."""

    def __init__(self, translator: BaseTranslator):
        self.translator = translator
        self.name = translator.name

    def translate(self, texts: list[str], target_lang: str) -> list[str]:
        protected_texts = []
        all_tokens: list[list[str]] = []
        for text in texts:
            protected, tokens = _protect_tokens(text)
            protected_texts.append(protected)
            all_tokens.append(tokens)
        translated = self.translator.translate(protected_texts, target_lang)
        return [_restore_tokens(t, tokens) for t, tokens in zip(translated, all_tokens)]


# Registry of all supported translation providers
AVAILABLE_TRANSLATORS = {
    "deepl": ("DeepL API", DeepLTranslator),
    "azure": ("Azure AI Translator", AzureTranslator),
    "gemini": ("Gemini (Google AI)", GeminiTranslator),
}

def get_available_translators() -> list[dict]:
    """Return a list of available translators based on environment variables."""
    available = []
    for key, (name, cls) in AVAILABLE_TRANSLATORS.items():
        try:
            # Instantiate to check if API key exists and is valid
            cls()
            available.append({"id": key, "name": name})
        except TranslationError:
            pass
    return available

def get_translator(fallback_order: list[str] | str) -> BaseTranslator:
    """Factory to return a FallbackTranslator based on the requested priority order.
    
    If priority order is empty or 'auto', uses all available in default order.
    """
    if isinstance(fallback_order, str):
        fallback_order = [fallback_order]
        
    if not fallback_order or fallback_order[0].lower() == "auto":
        fallback_order = list(AVAILABLE_TRANSLATORS.keys())
        
    cache = TranslationCache()
    translators: list[BaseTranslator] = []

    # Priority order first
    for provider_id in fallback_order:
        provider_id = provider_id.lower()
        if provider_id in AVAILABLE_TRANSLATORS:
            _, cls = AVAILABLE_TRANSLATORS[provider_id]
            try:
                translators.append(CachingTranslator(cls(), cache))
            except TranslationError as e:
                if provider_id == fallback_order[0].lower():
                    raise TranslationError(f"Failed to initialize requested provider '{provider_id}': {e}")
                pass

    # Append any available providers that weren't explicitly requested
    seen = {type(t.translator) for t in translators if isinstance(t, CachingTranslator)}
    for provider_id, (_, cls) in AVAILABLE_TRANSLATORS.items():
        if provider_id not in [p.lower() for p in fallback_order] and cls not in seen:
            try:
                translators.append(CachingTranslator(cls(), cache))
            except TranslationError:
                pass

    if not translators:
        raise TranslationError(
            "No translation provider configured or valid. "
            "Please add an API key (e.g. DEEPL_API_KEY) to your .env file."
        )

    result = translators[0] if len(translators) == 1 else FallbackTranslator(translators)
    return ProtectedTranslator(result)

if __name__ == "__main__":
    # Provides JSON output for the bash script to dynamically build CLI menus
    import json
    # Load dotenv in case it's called directly from CLI
    from dotenv import load_dotenv
    load_dotenv()
    
    print(json.dumps(get_available_translators()))
