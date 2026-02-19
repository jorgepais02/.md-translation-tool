"""Translate Markdown files to multiple languages via DeepL and generate documents.

Pipeline:
  1. Read .md file(s) from sources/
  2. Translate content to target languages via DeepL API
  3. Copy the original as es.md
  4. Generate DOCX with academic formatting per language
  5. Convert DOCX to PDF via LibreOffice (if available)

Output structure:
  translated/es/es.md + es.docx + es.pdf
  translated/en/en.md + en.docx + en.pdf
  translated/fr/fr.md + fr.docx + fr.pdf
  translated/ar/ar.md + ar.docx + ar.pdf
  translated/zh/zh.md + zh.docx + zh.pdf

Usage:
    python translation_pipeline.py                              # all .md in sources/
    python translation_pipeline.py sources/apuntes.md           # single file
    python translation_pipeline.py sources/apuntes.md --langs EN-GB FR
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv


# ═══════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════

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

MAX_BATCH_SIZE = 50


# ═══════════════════════════════════════════
# Markdown line classification
# ═══════════════════════════════════════════

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
BULLET_RE  = re.compile(r"^(\s*)-\s+(.*\S)\s*$")
NUMBER_RE  = re.compile(r"^(\s*)(\d+)\.\s+(.*\S)\s*$")
HR_RE      = re.compile(r"^\s*---\s*$")

LineInfo = tuple[str, str, str]


def parse_markdown_lines(lines: list[str]) -> list[LineInfo]:
    """Classify each Markdown line and extract translatable text.

    Returns a list of (kind, prefix, text) tuples where:
      - kind:   'blank', 'hr', 'heading', 'bullet', 'number', 'body'
      - prefix: structural prefix (hashes, indentation, number marker)
      - text:   the translatable content (empty for blank/hr)
    """
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


def rebuild_markdown_from_translations(
    parsed: list[LineInfo], translated_texts: list[str]
) -> list[str]:
    """Reconstruct the Markdown document using translated texts in order."""
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


# ═══════════════════════════════════════════
# DeepL API
# ═══════════════════════════════════════════

def translate_texts_via_deepl(texts: list[str], target_lang: str) -> list[str]:
    """Translate a list of text strings in batched DeepL API calls."""
    if not texts:
        return []

    if not DEEPL_API_KEY:
        print("ERROR: DEEPL_API_KEY not found in .env", file=sys.stderr)
        sys.exit(1)

    headers = {
        "Authorization": f"DeepL-Auth-Key {DEEPL_API_KEY}",
        "Content-Type": "application/json",
    }

    results: list[str] = []

    for i in range(0, len(texts), MAX_BATCH_SIZE):
        chunk = texts[i : i + MAX_BATCH_SIZE]
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


# ═══════════════════════════════════════════
# Document generation (DOCX + PDF)
# ═══════════════════════════════════════════

def generate_docx_document(md_file: Path, lang_code: str) -> Path:
    """Generate a DOCX from a translated .md file using document_generator."""
    from document_generator import convert_markdown_to_docx

    docx_file = md_file.with_suffix(".docx")
    convert_markdown_to_docx(md_file, docx_file, lang=lang_code)
    print(f"        DOCX → {docx_file.name}")
    return docx_file


def convert_docx_to_pdf(docx_file: Path) -> None:
    """Convert a DOCX file to PDF using LibreOffice in headless mode.

    If LibreOffice is not installed, prints a warning and skips silently.
    """
    outdir = docx_file.parent

    try:
        result = subprocess.run(
            [
                "soffice",
                "--headless",
                "--convert-to", "pdf",
                "--outdir", str(outdir),
                str(docx_file),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            pdf_name = docx_file.with_suffix(".pdf").name
            print(f"        PDF  → {pdf_name}")
        else:
            print(f"        ⚠ PDF conversion failed: {result.stderr.strip()}", file=sys.stderr)
    except FileNotFoundError:
        print(
            "        ⚠ LibreOffice not found — skipping PDF generation. "
            "Install with: brew install --cask libreoffice",
            file=sys.stderr,
        )
    except subprocess.TimeoutExpired:
        print("        ⚠ PDF conversion timed out", file=sys.stderr)


# ═══════════════════════════════════════════
# Pipeline orchestration
# ═══════════════════════════════════════════

def process_source_file(md_path: Path, langs: list[str]) -> None:
    """Translate one .md file and generate DOCX + PDF for each language.

    Output goes to translated/<lang>/<lang>.md, .docx, .pdf
    """
    lines = md_path.read_text(encoding="utf-8").splitlines()
    parsed = parse_markdown_lines(lines)

    # Collect translatable texts
    texts_to_translate = [text for kind, _pfx, text in parsed if text]

    if not texts_to_translate:
        print("  ⚠ No translatable text found.")
        return

    # 1. Copy original as es.md + DOCX + PDF
    es_folder = TRANSLATED_DIR / "es"
    es_folder.mkdir(parents=True, exist_ok=True)
    es_file = es_folder / "es.md"
    shutil.copy2(md_path, es_file)
    print(f"  ▸ es (original) → {es_file.relative_to(PROJECT_ROOT)}")
    docx_file = generate_docx_document(es_file, "es")
    convert_docx_to_pdf(docx_file)

    # 2. Translate to each target language
    for deepl_code in langs:
        short = LANG_MAP.get(deepl_code, deepl_code.lower().split("-")[0])
        print(f"  ▸ Translating to {short} ({deepl_code})…", end=" ", flush=True)

        translated = translate_texts_via_deepl(texts_to_translate, deepl_code)
        rebuilt = rebuild_markdown_from_translations(parsed, translated)

        lang_folder = TRANSLATED_DIR / short
        lang_folder.mkdir(parents=True, exist_ok=True)

        out_file = lang_folder / f"{short}.md"
        out_file.write_text("\n".join(rebuilt) + "\n", encoding="utf-8")
        print("OK")

        docx_file = generate_docx_document(out_file, short)
        convert_docx_to_pdf(docx_file)


# ═══════════════════════════════════════════
# CLI entry point
# ═══════════════════════════════════════════

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Translate Markdown files via DeepL and generate DOCX + PDF."
    )
    ap.add_argument(
        "md",
        type=Path,
        nargs="?",
        default=None,
        help="Specific .md file (if omitted, processes all files in sources/)",
    )
    ap.add_argument(
        "--langs",
        nargs="+",
        default=DEFAULT_LANGS,
        help=f"DeepL target language codes (default: {' '.join(DEFAULT_LANGS)})",
    )
    args = ap.parse_args()

    # Determine which files to process
    if args.md:
        files = [args.md.expanduser().resolve()]
    else:
        files = sorted(SOURCES_DIR.glob("*.md"))

    if not files:
        print("No .md files found in sources/", file=sys.stderr)
        sys.exit(1)

    TRANSLATED_DIR.mkdir(parents=True, exist_ok=True)

    for md_path in files:
        if not md_path.exists():
            print(f"ERROR: File not found: {md_path}", file=sys.stderr)
            continue

        print(f"\n{'='*60}")
        print(f"  File: {md_path.name}")
        print(f"{'='*60}")
        process_source_file(md_path, args.langs)

    print(f"\n✓ Pipeline complete. Output in: {TRANSLATED_DIR}")


if __name__ == "__main__":
    main()
