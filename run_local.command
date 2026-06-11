#!/bin/bash
set -e

cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required. Please install Python 3 first."
  read -r -p "Press Enter to close..."
  exit 1
fi

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo
echo "PDF app is starting..."
echo "Open this address in your browser:"
echo "http://127.0.0.1:8000"
echo

python pdf_extract_server.py
