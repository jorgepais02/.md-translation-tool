"""Translation cache backed by SQLite with WAL mode and auto-vacuum."""

import hashlib
import sqlite3
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DB_PATH = _PROJECT_ROOT / "cache" / "translations.db"
_VACUUM_THRESHOLD_MB = 50


class TranslationCache:
    def __init__(self, db_path: Path = _DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _init(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS translations (
                    key  TEXT PRIMARY KEY,
                    text TEXT NOT NULL
                )
            """)
        self._maybe_vacuum()

    def _maybe_vacuum(self) -> None:
        size_mb = self.db_path.stat().st_size / (1024 * 1024)
        if size_mb > _VACUUM_THRESHOLD_MB:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                conn.execute("VACUUM")

    @staticmethod
    def _key(text: str, lang: str, provider: str) -> str:
        raw = f"{text}\x00{lang}\x00{provider}".encode()
        return hashlib.sha256(raw).hexdigest()

    def get(self, text: str, lang: str, provider: str) -> str | None:
        key = self._key(text, lang, provider)
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT text FROM translations WHERE key = ?", (key,)
            ).fetchone()
        return row[0] if row else None

    def set(self, text: str, lang: str, provider: str, translation: str) -> None:
        key = self._key(text, lang, provider)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO translations (key, text) VALUES (?, ?)",
                (key, translation),
            )
