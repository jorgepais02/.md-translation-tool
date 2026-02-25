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
import itertools
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

from translators import get_translator, LANG_MAP, DEFAULT_LANGS

class Spinner:
    def __init__(self, message: str):
        self.message = message
        self.spinner = itertools.cycle(["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"])
        self.running = False
        self.task = None

    def spin(self):
        while self.running:
            sys.stdout.write(f"\r{self.message} {next(self.spinner)}")
            sys.stdout.flush()
            time.sleep(0.1)

    def start(self):
        self.running = True
        self.task = threading.Thread(target=self.spin, daemon=True)
        self.task.start()

    def stop(self, success_msg: str):
        self.running = False
        if self.task is not None:
            self.task.join()
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()
        print(f"{self.message} {success_msg}")

# ═══════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCES_DIR = PROJECT_ROOT / "sources"
TRANSLATED_DIR = PROJECT_ROOT / "translated"


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

def process_source_file(md_path: Path, langs: list[str], translator, use_google: bool = False, no_local: bool = False) -> None:
    """Translate one .md file and generate DOCX + PDF (local) or upload to Google Docs.

    Output goes to translated/<lang>/<lang>.md, .docx, .pdf
    """
    g_manager = None
    if use_google:
        from google_docs_manager import GoogleDocsManager
        try:
            g_manager = GoogleDocsManager()
        except Exception as e:
            print(f"ERROR: Google Docs Auth failed: {e}", file=sys.stderr)
            print("Please ensure credentials.json is present in the project root.", file=sys.stderr)
            sys.exit(1)

    lines = md_path.read_text(encoding="utf-8").splitlines()
    parsed = parse_markdown_lines(lines)

    # Collect translatable texts
    texts_to_translate = [text for kind, _pfx, text in parsed if text]

    if not texts_to_translate:
        print("  ⚠ No translatable text found.")
        return

    # 1. Handle original Spanish file
    if not no_local:
        es_folder = TRANSLATED_DIR / "es"
        es_folder.mkdir(parents=True, exist_ok=True)
        es_file = es_folder / "es.md"
        shutil.copy2(md_path, es_file)
        print(f"  ▸ {md_path.stem} (ES) → {es_file.relative_to(PROJECT_ROOT)}")
        docx_file = generate_docx_document(es_file, "es")
        convert_docx_to_pdf(docx_file)
    else:
        print(f"  ▸ {md_path.stem} (ES)")

    if g_manager:
        spinner = Spinner("      ☁️  Uploading to Google Drive...")
        spinner.start()
        try:
            doc_id = g_manager.create_document(f"ES - {md_path.stem}")
            # Setup layout: Header with image + Footer with page numbers
            header_img = PROJECT_ROOT / "public" / "header.png"
            g_manager.setup_document_layout(doc_id, header_image_path=header_img, is_rtl=False)
            g_manager.upload_markdown_content(doc_id, lines, "es")
            doc_url = g_manager.get_document_url(doc_id)
            if not hasattr(process_source_file, "generated_links"):
                process_source_file.generated_links = {}
            process_source_file.generated_links["es"] = doc_url
            spinner.stop("✓")
        except Exception as e:
            spinner.stop("❌")
            print(f"      Error: {e}")

    # 2. Translate to each target language
    for lang_code in langs:
        short = LANG_MAP.get(lang_code, lang_code.lower().split("-")[0])
        
        spinner = Spinner(f"  ▸ Translating to {short.upper()} ({lang_code})…")
        spinner.start()
        try:
            translated = translator.translate(texts_to_translate, lang_code)
            rebuilt = rebuild_markdown_from_translations(parsed, translated)
            spinner.stop("✓")
        except Exception as e:
            spinner.stop("❌")
            print(f"      Error: {e}")
            continue

        # Local output
        if not no_local:
            lang_folder = TRANSLATED_DIR / short
            lang_folder.mkdir(parents=True, exist_ok=True)
            out_file = lang_folder / f"{short}.md"
            out_file.write_text("\n".join(rebuilt) + "\n", encoding="utf-8")
            
            docx_file = generate_docx_document(out_file, short)
            convert_docx_to_pdf(docx_file)

        # Google Docs output
        if g_manager:
            spinner = Spinner("      ☁️  Uploading to Google Drive...")
            spinner.start()
            try:
                doc_id = g_manager.create_document(f"{short.upper()} - {md_path.stem}")
                # Setup layout: Header with image + Footer with page numbers
                header_img = PROJECT_ROOT / "public" / "header.png"
                is_rtl = short in ["ar", "he", "fa", "ur"]
                g_manager.setup_document_layout(doc_id, header_image_path=header_img, is_rtl=is_rtl)
                g_manager.upload_markdown_content(doc_id, rebuilt, short)
                doc_url = g_manager.get_document_url(doc_id)
                if not hasattr(process_source_file, "generated_links"):
                    process_source_file.generated_links = {}
                process_source_file.generated_links[short] = doc_url
                spinner.stop("✓")
            except Exception as e:
                spinner.stop("❌")
                print(f"      Error: {e}")



# ═══════════════════════════════════════════
# CLI entry point
# ═══════════════════════════════════════════

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Translate Markdown files via selected provider and generate DOCX + PDF."
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
        help=f"Target language codes (default: {' '.join(DEFAULT_LANGS)})",
    )
    ap.add_argument(
        "--provider",
        choices=["deepl", "azure"],
        default="deepl",
        help="Translation provider to use (default: deepl)",
    )
    ap.add_argument(
        "--google",
        action="store_true",
        help="Upload translated documents directly to Google Docs",
    )
    ap.add_argument(
        "--no-local",
        action="store_true",
        help="Skip generating local DOCX and PDF (useful if using Google Docs output instead)",
    )
    args = ap.parse_args()

    # Initialize translator
    try:
        translator = get_translator(args.provider)
    except Exception as e:
        print(f"ERROR: Failed to initialize translator: {e}", file=sys.stderr)
        sys.exit(1)

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
        process_source_file(md_path, args.langs, translator, use_google=args.google, no_local=args.no_local)

    if args.no_local and args.google:
        print(f"\n✓ Pipeline complete. Documents uploaded to Google Drive.")
    elif args.no_local and not args.google:
        print(f"\n✓ Pipeline complete. Markdown strings translated in: {TRANSLATED_DIR}")
    else:
        print(f"\n✓ Pipeline complete. Output in: {TRANSLATED_DIR}")
        
    if getattr(process_source_file, "generated_links", None):
        print("\nGoogle Docs Links:")
        for lang, link in process_source_file.generated_links.items():
            print(f"  [{lang.upper()}] \033]8;;{link}\033\\{link}\033]8;;\033\\")


if __name__ == "__main__":
    main()
