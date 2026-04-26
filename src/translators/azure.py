import os
import requests
from .base import BaseTranslator, TranslationError


class AzureTranslator(BaseTranslator):
    """Translator strategy using Azure AI Translator API."""

    name = "azure"

    def __init__(self, api_key: str | None = None, region: str | None = None):
        self.api_key = api_key or os.getenv("AZURE_TRANSLATOR_KEY", "")
        self.region = region or os.getenv("AZURE_TRANSLATOR_REGION", "")
        if not self.api_key:
            raise TranslationError("AZURE_TRANSLATOR_KEY not found in .env")

        self.translate_url = "https://api.cognitive.microsofttranslator.com/translate"
        self.max_batch_size = 100

    def _map_lang_code(self, lang: str) -> str:
        if lang.upper() == "EN-GB":
            return "en-GB"
        if lang.upper() == "ZH":
            return "zh-Hans"
        return lang.lower()

    def translate(self, texts: list[str], target_lang: str) -> list[str]:
        if not texts:
            return []

        headers = {"Ocp-Apim-Subscription-Key": self.api_key, "Content-type": "application/json"}
        if self.region:
            headers["Ocp-Apim-Subscription-Region"] = self.region

        results: list[str] = []
        params = {"api-version": "3.0", "to": [self._map_lang_code(target_lang)]}

        for i in range(0, len(texts), self.max_batch_size):
            chunk = texts[i: i + self.max_batch_size]
            payload = [{"text": t} for t in chunk]
            try:
                resp = requests.post(self.translate_url, params=params, json=payload, headers=headers, timeout=60)
                if resp.status_code == 403:
                    msg = f"Azure API Error (403). Check your tier quota or valid region."
                    if "out of call volume quota" in resp.text.lower():
                        msg += " Quota exceeded."
                    raise TranslationError(msg)
                resp.raise_for_status()
                for item in resp.json():
                    results.append(item["translations"][0]["text"])
            except requests.exceptions.RequestException as e:
                detail = ""
                if hasattr(e, "response") and e.response is not None:
                    detail = f" — {e.response.text}"
                raise TranslationError(f"Azure API request failed: {e}{detail}") from e

        return results
