@echo off
cd /d "%~dp0"
echo Ativando ambiente virtual...
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo [ERRO] Ambiente virtual (.venv ou venv) nao encontrado!
    pause
    exit /b
)

echo Iniciando automacao...
python cadastro.py
pause
