"""Core pipeline utilities for mdtranslator.

This module is a library — it has no CLI entry point.
The CLI lives in src/cli/. Import from here:

    from translation_pipeline import (
        parse_markdown_lines,
        rebuild_markdown_from_translations,
        generate_docx_document,
        convert_docx_to_pdf,
        TRANSLATED_DIR,
        DRIVE_FOLDER_ID,
        CONFIG,
    )
"""

from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path


# ═══════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════

PROJECT_ROOT   = Path(__file__).resolve().parent.parent
SOURCES_DIR    = PROJECT_ROOT / "sources"
TRANSLATED_DIR = PROJECT_ROOT / "translated"
DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "").strip()


def load_config() -> dict:
    """Load user config from config.json, falling back to config.example.json."""
    for name in ("config.json", "config.example.json"):
        p = PROJECT_ROOT / name
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    return {"drive": {}, "document": {}}


CONFIG = load_config()

DEFAULT_LANGS = CONFIG.get("document", {}).get("default_languages", ["EN", "FR", "AR", "ZH"])


# ═══════════════════════════════════════════
# Markdown line classification
# ═══════════════════════════════════════════

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
BULLET_RE  = re.compile(r"^(\s*)-\s+(.*\S)\s*$")
NUMBER_RE  = re.compile(r"^(\s*)(\d+)\.\s+(.*\S)\s*$")
HR_RE      = re.compile(r"^\s*---\s*$")
FENCE_RE   = re.compile(r"^(`{3,}|~{3,})")

LineInfo = tuple[str, str, str]


def parse_markdown_lines(lines: list[str]) -> list[LineInfo]:
    """Classify each Markdown line and extract translatable text.

    Returns a list of (kind, prefix, text) tuples where:
      - kind:   'blank' | 'hr' | 'heading' | 'bullet' | 'number' | 'body' | 'code_block'
      - prefix: structural prefix (hashes, indentation, number marker, or raw line for code_block)
      - text:   translatable content (empty for blank/hr/code_block)
    """
    parsed: list[LineInfo] = []
    in_code = False
    fence   = ""

    for raw in lines:
        line = raw.rstrip("\n")

        m = FENCE_RE.match(line)
        if m:
            if not in_code:
                in_code, fence = True, m.group(1)
            elif line.strip().startswith(fence):
                in_code, fence = False, ""
            parsed.append(("code_block", line, ""))
            continue

        if in_code:
            parsed.append(("code_block", line, ""))
            continue

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
            parsed.append(("number", f"{m.group(1)}{m.group(2)}.", m.group(3)))
            continue

        parsed.append(("body", "", line.strip()))

    return parsed


def rebuild_markdown_from_translations(
    parsed: list[LineInfo], translated_texts: list[str]
) -> list[str]:
    """Reconstruct the Markdown document using translated texts in order."""
    out: list[str] = []
    t_idx = 0

    for kind, prefix, _ in parsed:
        if kind == "blank":
            out.append("")
        elif kind == "hr":
            out.append("---")
        elif kind == "code_block":
            out.append(prefix)
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
    """Generate a DOCX from a translated .md file using document_converter."""
    from document_converter import convert

    docx_file   = md_file.with_suffix(".docx")
    header_cfg  = CONFIG.get("document", {}).get("header_image")
    header_img  = Path("public/header.png") if not header_cfg else (PROJECT_ROOT / header_cfg)

    convert(md_file, docx_file, lang=lang_code, header=header_img)
    return docx_file


def _soffice_exe() -> str:
    """Return the soffice executable path, preferring the macOS app bundle."""
    if platform.system() == "Darwin":
        mac_path = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
        if Path(mac_path).exists():
            return mac_path
    return "soffice"


def convert_docx_to_pdf(docx_file: Path) -> None:
    """Convert a DOCX to PDF using LibreOffice headless.

    Uses --norestore --nofirststartwizard --nologo to prevent the GUI
    from opening (important on macOS).
    Skips silently if LibreOffice is not installed.
    """
    outdir = docx_file.parent
    try:
        result = subprocess.run(
            [
                _soffice_exe(),
                "--headless",
                "--norestore",
                "--nofirststartwizard",
                "--nologo",
                "--convert-to", "pdf",
                "--outdir", str(outdir),
                str(docx_file),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(f"PDF conversion failed: {result.stderr.strip()}")
    except FileNotFoundError:
        raise RuntimeError("LibreOffice not found — install: brew install --cask libreoffice")
    except subprocess.TimeoutExpired:
        raise RuntimeError("PDF conversion timed out")