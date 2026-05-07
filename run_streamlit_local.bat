@echo off
setlocal
cd /d "%~dp0"

if not exist .venv\Scripts\python.exe (
    echo [setup] Creando entorno virtual...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo [setup] Instalando dependencias...
pip install -q --upgrade pip
pip install -q -r streamlit_app\requirements.txt

echo.
echo [run] Lanzando Streamlit en http://localhost:8501
echo Para salir, cierra esta ventana o presiona Ctrl+C.
echo.

streamlit run streamlit_app\app.py
endlocal
