"""Markdown line classifier and rebuilder for the translation pipeline."""

from __future__ import annotations
import re

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
