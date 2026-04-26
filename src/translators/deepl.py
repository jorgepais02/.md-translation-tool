import os
import requests
from .base import BaseTranslator, TranslationError


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
            chunk = texts[i: i + self.max_batch_size]
            payload = {"text": chunk, "target_lang": target_lang}
            try:
                resp = requests.post(self.translate_url, json=payload, headers=headers, timeout=60)
                if resp.status_code == 456:
                    raise TranslationError("DeepL quota exceeded.")
                resp.raise_for_status()
                for item in resp.json()["translations"]:
                    results.append(item["text"])
            except requests.exceptions.RequestException as e:
                raise TranslationError(f"DeepL API request failed: {e}") from e

        return results
