#!/bin/bash
set -e

cd "$(dirname "$0")/multilingual_pdf_study_helper"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run app.py --server.port 8502
