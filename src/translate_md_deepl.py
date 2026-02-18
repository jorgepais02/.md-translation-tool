"""Traduce archivos Markdown de sources/ a varios idiomas con DeepL y genera DOCX.

Flujo completo:
  1. Lee cada .md de sources/
  2. Traduce a EN-GB, FR, AR, ZH con DeepL
  3. Copia el original como es.md
  4. Genera DOCX con make_notes.py por cada .md traducido

Estructura de salida:
  translated/<stem>/es.md   + es.docx
  translated/<stem>/en.md   + en.docx
  translated/<stem>/ar.md   + ar.docx
  translated/<stem>/zh.md   + zh.docx
  translated/<stem>/fr.md   + fr.docx

Uso:
    python translate_md_deepl.py                          # procesa todos los .md de sources/
    python translate_md_deepl.py sources/apuntes.md       # un archivo concreto
    python translate_md_deepl.py sources/apuntes.md --langs EN-GB FR
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

# ---------------------
# Configuration
# ---------------------

load_dotenv()

DEEPL_API_KEY = os.getenv("DEEPL_API_KEY", "")

# Keys ending in ":fx" belong to the free plan → api-free.deepl.com
if DEEPL_API_KEY.endswith(":fx"):
    DEEPL_BASE = "https://api-free.deepl.com"
else:
    DEEPL_BASE = "https://api.deepl.com"

TRANSLATE_URL = f"{DEEPL_BASE}/v2/translate"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCES_DIR = PROJECT_ROOT / "sources"
TRANSLATED_DIR = PROJECT_ROOT / "translated"

# DeepL code → short filename code
LANG_MAP = {
    "EN-GB": "en",
    "FR":    "fr",
    "AR":    "ar",
    "ZH":    "zh",
}

DEFAULT_LANGS = list(LANG_MAP.keys())

# ---------------------
# Markdown regex
# ---------------------

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
BULLET_RE  = re.compile(r"^(\s*)-\s+(.*\S)\s*$")
NUMBER_RE  = re.compile(r"^(\s*)(\d+)\.\s+(.*\S)\s*$")
HR_RE      = re.compile(r"^\s*---\s*$")


# ---------------------
# DeepL API
# ---------------------

def translate_batch(texts: list[str], target_lang: str) -> list[str]:
    """Translate a list of texts in a single DeepL API call."""
    if not texts:
        return []

    if not DEEPL_API_KEY:
        print("ERROR: DEEPL_API_KEY no encontrada en .env", file=sys.stderr)
        sys.exit(1)

    headers = {
        "Authorization": f"DeepL-Auth-Key {DEEPL_API_KEY}",
        "Content-Type": "application/json",
    }

    MAX_BATCH = 50
    results: list[str] = []

    for i in range(0, len(texts), MAX_BATCH):
        chunk = texts[i : i + MAX_BATCH]
        payload = {
            "text": chunk,
            "target_lang": target_lang,
        }

        resp = requests.post(TRANSLATE_URL, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        for item in data["translations"]:
            results.append(item["text"])

    return results


# ---------------------
# Markdown parse → translate → rebuild
# ---------------------

LineInfo = tuple[str, str, str]


def parse_lines(lines: list[str]) -> list[LineInfo]:
    """Classify each line and extract the translatable text."""
    parsed: list[LineInfo] = []

    for raw in lines:
        line = raw.rstrip("\n")

        if not line.strip():
            parsed.append(("blank", "", ""))
            continue

        if HR_RE.match(line):
            parsed.append(("hr", "---", ""))
            continue

        m = HEADING_RE.match(line)
        if m:
            parsed.append(("heading", m.group(1), m.group(2)))
            continue

        m = BULLET_RE.match(line)
        if m:
            parsed.append(("bullet", m.group(1), m.group(2)))
            continue

        m = NUMBER_RE.match(line)
        if m:
            prefix = f"{m.group(1)}{m.group(2)}."
            parsed.append(("number", prefix, m.group(3)))
            continue

        parsed.append(("body", "", line.strip()))

    return parsed


def rebuild_lines(parsed: list[LineInfo], translated_texts: list[str]) -> list[str]:
    """Reconstruct the Markdown using translated texts in order."""
    out: list[str] = []
    t_idx = 0

    for kind, prefix, _original in parsed:
        if kind == "blank":
            out.append("")
        elif kind == "hr":
            out.append("---")
        elif kind == "heading":
            out.append(f"{prefix} {translated_texts[t_idx]}")
            t_idx += 1
        elif kind == "bullet":
            out.append(f"{prefix}- {translated_texts[t_idx]}")
            t_idx += 1
        elif kind == "number":
            out.append(f"{prefix} {translated_texts[t_idx]}")
            t_idx += 1
        elif kind == "body":
            out.append(translated_texts[t_idx])
            t_idx += 1

    return out


# ---------------------
# DOCX generation (delegates to make_notes)
# ---------------------

def generate_docx(md_file: Path, lang_code: str) -> None:
    """Generate a DOCX from a translated .md file using make_notes.py."""
    from make_notes import md_to_docx
    docx_file = md_file.with_suffix(".docx")
    md_to_docx(md_file, docx_file, lang=lang_code)
    print(f"        DOCX → {docx_file.name}")


# ---------------------
# Main logic
# ---------------------

def process_file(md_path: Path, langs: list[str]) -> None:
    """Translate one .md file and generate DOCX for each language."""
    stem = md_path.stem
    out_folder = TRANSLATED_DIR / stem
    out_folder.mkdir(parents=True, exist_ok=True)

    lines = md_path.read_text(encoding="utf-8").splitlines()
    parsed = parse_lines(lines)

    # Collect translatable texts
    texts_to_translate = [text for kind, _pfx, text in parsed if text]

    if not texts_to_translate:
        print("  ⚠ No hay texto para traducir.")
        return

    # 1. Copy original as es.md + DOCX
    es_file = out_folder / "es.md"
    shutil.copy2(md_path, es_file)
    print(f"  ▸ es (original) → {es_file.relative_to(PROJECT_ROOT)}")
    generate_docx(es_file, "es")

    # 2. Translate to each target language
    for deepl_code in langs:
        short = LANG_MAP.get(deepl_code, deepl_code.lower().split("-")[0])
        print(f"  ▸ Traduciendo a {short} ({deepl_code})…", end=" ", flush=True)

        translated = translate_batch(texts_to_translate, deepl_code)
        rebuilt = rebuild_lines(parsed, translated)

        out_file = out_folder / f"{short}.md"
        out_file.write_text("\n".join(rebuilt) + "\n", encoding="utf-8")
        print("OK")

        generate_docx(out_file, short)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Traduce archivos Markdown con DeepL y genera DOCX."
    )
    ap.add_argument(
        "md",
        type=Path,
        nargs="?",
        default=None,
        help="Archivo .md concreto (si no se indica, procesa todos los de sources/)",
    )
    ap.add_argument(
        "--langs",
        nargs="+",
        default=DEFAULT_LANGS,
        help=f"Códigos DeepL destino (default: {' '.join(DEFAULT_LANGS)})",
    )
    args = ap.parse_args()

    # Determine which files to process
    if args.md:
        files = [args.md.expanduser().resolve()]
    else:
        files = sorted(SOURCES_DIR.glob("*.md"))

    if not files:
        print("No se encontraron archivos .md en sources/", file=sys.stderr)
        sys.exit(1)

    TRANSLATED_DIR.mkdir(parents=True, exist_ok=True)

    for md_path in files:
        if not md_path.exists():
            print(f"ERROR: No existe {md_path}", file=sys.stderr)
            continue

        print(f"\n{'='*60}")
        print(f"  Archivo: {md_path.name}")
        print(f"{'='*60}")
        process_file(md_path, args.langs)

    print(f"\n✓ Todo completado. Salida en: {TRANSLATED_DIR}")


if __name__ == "__main__":
    main()
