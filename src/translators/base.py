import re as _re
from abc import ABC, abstractmethod


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


class TranslationError(Exception):
    """Raised when a translation provider fails."""
    pass


class BaseTranslator(ABC):
    """Abstract base class for all translation providers."""

    name: str = "unknown"

    @abstractmethod
    def translate(self, texts: list[str], target_lang: str) -> list[str]:
        """Translate a list of strings to target_lang. Returns same-length list."""
        pass


class FallbackTranslator(BaseTranslator):
    """Tries multiple providers in order, falling back on failure."""

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


class ProtectedTranslator(BaseTranslator):
    """Wraps any translator to protect inline code spans, formulas, and URLs."""

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
