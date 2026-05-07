@echo off
setlocal
cd /d "%~dp0"

if not exist .venv\Scripts\python.exe (
    echo [setup] Creando entorno virtual...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo [setup] Instalando dependencias del dev console...
pip install -q --upgrade pip
pip install -q -r dev_console\requirements.txt

echo.
echo [run] Lanzando consola de desarrollo...
echo.

python dev_console\console.py
endlocal
