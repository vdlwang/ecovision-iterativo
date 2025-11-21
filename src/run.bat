@echo off
echo ========================================
echo  EcoVision - Inicializacao Completa
echo ========================================
echo.

REM Verificar se Python esta instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado. Instale Python 3.8+
    pause
    exit /b 1
)

REM Verificar se Node esta instalado
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Node.js nao encontrado. Instale Node.js 16+
    pause
    exit /b 1
)

echo [1/3] Iniciando Backend Python...
start "EcoVision Backend" cmd /k "cd backend && python ecovision_local.py"
timeout /t 3 /nobreak >nul

echo [2/3] Iniciando Frontend React...
start "EcoVision Frontend" cmd /k "npm run dev"
timeout /t 2 /nobreak >nul

echo [3/3] Sistema iniciado!
echo.
echo Backend: Python rodando em ws://localhost:8765
echo Frontend: React rodando em http://localhost:5173
echo.
echo Pressione qualquer tecla para abrir navegador...
pause >nul
start http://localhost:5173
