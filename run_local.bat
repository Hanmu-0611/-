@echo off
cd /d "%~dp0"

python -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo.
echo PDF app is starting...
echo Open this address in your browser:
echo http://127.0.0.1:8000
echo.

python pdf_extract_server.py
pause
