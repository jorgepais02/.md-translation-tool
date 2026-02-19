#!/usr/bin/env bash
# -----------------------------------------------------------
# run_pipeline.sh — Translate a Markdown file to EN, FR, AR, ZH
#                   and generate DOCX + PDF documents.
#
# Usage:
#   ./run_pipeline.sh path/to/document.md
#   ./run_pipeline.sh sources/apuntes.md
# -----------------------------------------------------------

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ $# -lt 1 ]; then
  echo "Usage: $0 <path-to-file.md>"
  exit 1
fi

MD_FILE="$1"

if [ ! -f "$MD_FILE" ]; then
  echo "ERROR: File not found: '$MD_FILE'"
  exit 1
fi

# Activate virtual environment
source "$SCRIPT_DIR/.venv/bin/activate"

# Run the full translation pipeline
python "$SCRIPT_DIR/src/translation_pipeline.py" "$MD_FILE"
