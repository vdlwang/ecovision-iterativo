@echo off
echo ========================================
echo EcoVision - Sistema de Reciclagem
echo ========================================
echo.

echo [1/2] Iniciando Backend Python...
cd backend
start cmd /k "python ecovision_local.py"

echo [2/2] Frontend React ja esta rodando no Figma Make
echo.
echo ========================================
echo Sistema iniciado!
echo ========================================
echo.
echo Backend: http://localhost:8765
echo Frontend: Verifique o Figma Make
echo.
echo Pressione qualquer tecla para encerrar...
pause >nul
