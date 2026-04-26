"""
Convierte MD a DOCX via Pandoc + postprocess.

API:
    convert(md_path, output_path, lang, header=None) -> Path

CLI:
    python -m src.document.converter input.md -o output.docx --lang ar --header public/header.png
"""

import argparse, subprocess, sys
from pathlib import Path

from .postprocess import postprocess

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"

RTL_LANGS = {"ar", "he", "fa", "ur"}
CJK_LANGS = {"zh", "ja", "ko", "vi"}


def get_template(lang: str) -> Path:
    if lang in RTL_LANGS:
        return TEMPLATES_DIR / "template_rtl.docx"
    return TEMPLATES_DIR / "template_ltr.docx"


def _pandoc(md_path: Path, output_path: Path, template: Path):
    cmd = [
        "pandoc", str(md_path),
        "--reference-doc", str(template),
        "--shift-heading-level-by=-1",
        "--no-highlight",
        "-o", str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Pandoc failed:\n{result.stderr}")


def convert(
    md_path:     Path,
    output_path: Path,
    lang:        str,
    header:      Path | None = None,
) -> Path:
    """
    md_path     — MD de entrada (con frontmatter YAML title:)
    output_path — DOCX de salida
    lang        — código ISO (es, en, ar, zh, ja, ...)
    header      — imagen PNG para cabecera (opcional)
    """
    md_path     = Path(md_path).resolve()
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    template = get_template(lang)
    if not template.exists():
        raise FileNotFoundError(f"Template not found: {template}")

    _pandoc(md_path, output_path, template)
    postprocess(output_path, lang=lang, header=header)

    return output_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input",          type=Path)
    ap.add_argument("-o", "--output", type=Path, default=None)
    ap.add_argument("--lang",         default="es")
    ap.add_argument("--header",       type=Path, default=None)
    args = ap.parse_args()

    out = args.output or args.input.with_suffix(".docx")
    try:
        result = convert(args.input, out, args.lang, args.header)
        print(f"✓ {result}")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
