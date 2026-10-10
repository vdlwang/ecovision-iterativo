@echo off
REM EcoVision - Script de Desenvolvimento para Windows
REM Inicia servidor de inferência Python

setlocal enabledelayedexpansion

echo.
echo ====================================
echo   EcoVision - Sistema de Reciclagem
echo   Modo Desenvolvimento (Windows)
echo ====================================
echo.

REM Verificar Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python nao encontrado!
    echo Instale Python 3.8+ de https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Python instalado
python --version

REM Verificar ambiente virtual
if not exist "venv\" (
    echo [INFO] Criando ambiente virtual...
    python -m venv venv
    echo [OK] Ambiente virtual criado
)

REM Ativar ambiente virtual
echo [INFO] Ativando ambiente virtual...
call venv\Scripts\activate.bat

REM Instalar dependencias
echo [INFO] Verificando dependencias...
python -c "import ultralytics" >nul 2>nul
if %errorlevel% neq 0 (
    echo [INFO] Instalando dependencias Python...
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    echo [OK] Dependencias instaladas
) else (
    echo [OK] Dependencias ja instaladas
)

REM Executar verificacao
echo.
echo ====================================
echo   Verificando Sistema
echo ====================================
echo.
python test_setup.py

REM Perguntar se deseja continuar
echo.
set /p continue="Iniciar servidor de inferencia? (S/N): "
if /i not "%continue%"=="S" (
    echo [INFO] Abortado pelo usuario
    exit /b 0
)

REM Criar pasta de logs
if not exist "logs\" mkdir logs

REM Iniciar servidor Python
echo.
echo ====================================
echo   Iniciando Servidor Python
echo ====================================
echo.
echo [INFO] Iniciando servidor de inferencia...
echo [INFO] Logs sendo salvos em: logs\inference.log
echo.

start /b python inference_server.py > logs\inference.log 2>&1

REM Aguardar servidor iniciar
echo [INFO] Aguardando servidor inicializar...
timeout /t 5 /nobreak >nul

REM Verificar se servidor esta rodando
curl -s http://localhost:8000/health >nul 2>nul
if %errorlevel% equ 0 (
    echo [OK] Servidor Python esta respondendo!
) else (
    echo [ERROR] Servidor Python nao esta respondendo
    echo [INFO] Verifique os logs: type logs\inference.log
    pause
    exit /b 1
)

echo.
echo ====================================
echo   Servidores em Execucao
echo ====================================
echo.
echo [OK] Servidor Python: http://localhost:8000
echo [OK] Documentacao API: http://localhost:8000/docs
echo [OK] Logs: logs\inference.log
echo.
echo Para iniciar o frontend, execute em outro terminal:
echo   npm run dev
echo.
echo Para parar o servidor:
echo   Pressione Ctrl+C
echo.
echo ====================================
echo   Sistema Pronto!
echo ====================================
echo.

REM Manter janela aberta
pause
