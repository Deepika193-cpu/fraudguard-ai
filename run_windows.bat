@echo off
setlocal

if not exist ".venv\Scripts\python.exe" (
    echo Creating Python virtual environment...
    py -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

if not exist ".env" copy ".env.example" ".env" >nul

echo.
echo Starting FraudGuard AI at http://127.0.0.1:5000
echo Press Ctrl+C to stop the server.
echo.
python app.py

endlocal
