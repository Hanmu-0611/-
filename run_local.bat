@echo off
cd /d "%~dp0"
cd multilingual_pdf_study_helper

python -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo.
echo Streamlit app is starting...
echo Open this address in your browser:
echo http://localhost:8502
echo.

python -m streamlit run app.py --server.port 8502
pause
