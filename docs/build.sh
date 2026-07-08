#!/bin/bash

# Build script for sphinxpress documentation

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Building sphinxpress documentation...${NC}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"

if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

echo -e "${YELLOW}Installing documentation requirements...${NC}"
python -m pip install -r "$SCRIPT_DIR/requirements.txt"

echo -e "${YELLOW}Installing sphinxpress in development mode...${NC}"
python -m pip install -e "$PROJECT_ROOT"

echo -e "${YELLOW}Cleaning previous build...${NC}"
rm -rf "$SCRIPT_DIR/_build/"

echo -e "${YELLOW}Building HTML documentation...${NC}"
sphinx-build -b html "$SCRIPT_DIR" "$SCRIPT_DIR/_build/html"

if command -v pdflatex &>/dev/null; then
    echo -e "${YELLOW}Building PDF documentation...${NC}"
    sphinx-build -b latex "$SCRIPT_DIR" "$SCRIPT_DIR/_build/latex"
    cd "$SCRIPT_DIR/_build/latex"
    make
else
    echo -e "${YELLOW}pdflatex not found, skipping PDF build${NC}"
fi

echo -e "${GREEN}Documentation build complete.${NC}"
echo -e "${GREEN}HTML documentation: $SCRIPT_DIR/_build/html/index.html${NC}"
if [ -f "$SCRIPT_DIR/_build/latex/sphinxpress.pdf" ]; then
    echo -e "${GREEN}PDF documentation: $SCRIPT_DIR/_build/latex/sphinxpress.pdf${NC}"
fi
