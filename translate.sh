#!/usr/bin/env bash
# -----------------------------------------------------------
# translate.sh — Traduce un .md a EN, FR, AR, ZH y genera DOCX
#
# Uso:
#   ./translate.sh ruta/al/documento.md
#   ./translate.sh sources/apuntes.md
# -----------------------------------------------------------

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ $# -lt 1 ]; then
  echo "Uso: $0 <ruta-al-archivo.md>"
  exit 1
fi

MD_FILE="$1"

if [ ! -f "$MD_FILE" ]; then
  echo "ERROR: No existe el archivo '$MD_FILE'"
  exit 1
fi

# Activar entorno virtual
source "$SCRIPT_DIR/.venv/bin/activate"

# Ejecutar pipeline completo
python "$SCRIPT_DIR/src/translate_md_deepl.py" "$MD_FILE"
