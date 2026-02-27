#!/usr/bin/env bash
# -----------------------------------------------------------
# run_pipeline.sh — Interactive Markdown Translation CLI
# -----------------------------------------------------------

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ANSI Colors for beautiful CLI
BLUE='\033[1;34m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
DIM='\033[2m'
NC='\033[0m' # No Color

echo -e "${BLUE}==============================================${NC}"
echo -e "${BLUE}   Markdown Translation & Formatting Tool   ${NC}"
echo -e "${BLUE}==============================================${NC}"

# Ensure source file is provided
if [ $# -gt 0 ]; then
  MD_FILE="$1"
else
  echo -e "${YELLOW}Please provide the path to the Markdown file:${NC}"
  read -p "> " MD_FILE
fi

if [ ! -f "$MD_FILE" ]; then
  echo -e "${RED}ERROR: File not found: '$MD_FILE'${NC}"
  exit 1
fi

echo -e "\n${GREEN}File selected:${NC} $MD_FILE"

# 1. Select Provider
echo -e "\n${YELLOW}Which translation provider would you like to use?${NC}"
echo "  1) Auto — uses all available APIs with automatic fallback (Recommended)"
echo "  2) DeepL API"
echo "  3) Azure AI Translator"
echo ""
read -p "Select [1-3] (default: 1): " PROVIDER_CHOICE

case "$PROVIDER_CHOICE" in
  2) PROVIDER="deepl" ;;
  3) PROVIDER="azure" ;;
  *) PROVIDER="auto" ;;
esac
echo -e "Provider set to: ${GREEN}$PROVIDER${NC}"

# 2. Select Output Mode
echo -e "\n${YELLOW}Where do you want to generate the documents?${NC}"
echo "  1) Local only (.docx and .pdf)"
echo "  2) Google Drive only (Google Docs layout with perfect RTL)"
echo "  3) Both Local and Google Drive"
echo ""
read -p "Select [1-3] (default: 3): " DRIVE_CHOICE

DRIVE_FLAG=""
case "$DRIVE_CHOICE" in
  1) DRIVE_FLAG="" ;;
  2) DRIVE_FLAG="--drive --cloud-only" ;;
  *) DRIVE_FLAG="--drive" ;;
esac

echo -e "Google Drive generation: ${GREEN}$(if [ "$DRIVE_CHOICE" = "1" ]; then echo "OFF"; else echo "ON"; fi)${NC}"

# 3. Select Languages
echo -e "\n${YELLOW}Enter Target Language Codes separated by space:${NC}"
echo -e "  ${DIM}Supports ANY ISO code. Common examples: EN, FR, AR, ZH${NC}"
echo -e "  ${DIM}Leave empty to apply defaults (EN FR AR ZH).${NC}"
echo ""
read -p "> " LANGS_INPUT

if [ -z "$LANGS_INPUT" ]; then
  LANGS="EN-GB FR AR ZH"
else
  LANGS="$LANGS_INPUT"
fi
echo -e "Target languages: ${GREEN}$LANGS${NC}"

# Confirm and Run
echo -e "\n\n${BLUE}==============================================${NC}"
echo "Starting Translation Pipeline..."
echo -e "${BLUE}==============================================${NC}"

# Verify virtual environment exists
if [ ! -d "$SCRIPT_DIR/.venv" ]; then
  echo -e "${RED}ERROR: Virtual environment not found. Please setup the project first.${NC}"
  exit 1
fi

# Activate virtual environment
source "$SCRIPT_DIR/.venv/bin/activate"

# Build command dynamically
CMD="python \"$SCRIPT_DIR/src/translation_pipeline.py\" \"$MD_FILE\" --provider \"$PROVIDER\" -l $LANGS"
if [ -n "$DRIVE_FLAG" ]; then
  CMD="$CMD $DRIVE_FLAG"
fi

eval $CMD

echo -e "\n${GREEN}Pipeline finished successfully!${NC}"
