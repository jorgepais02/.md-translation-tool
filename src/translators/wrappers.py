from .base import BaseTranslator, TranslationError
from .cache import TranslationCache


class CachingTranslator(BaseTranslator):
    """Transparent cache wrapper — checks SQLite before calling the provider."""

    def __init__(self, translator: BaseTranslator, cache: TranslationCache):
        self.translator = translator
        self.cache = cache
        self.name = translator.name

    def translate(self, texts: list[str], target_lang: str) -> list[str]:
        results: list[str | None] = []
        miss_idx: list[int] = []
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
