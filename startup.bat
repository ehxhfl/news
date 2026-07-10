@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
"%LocalAppData%\Programs\Python\Python312\python.exe" main.py || exit /b 1
start index.html
