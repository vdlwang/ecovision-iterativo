@echo off
REM EcoVision - Setup Automático de Modelos YOLO (Windows)
setlocal enabledelayedexpansion

echo =============================================
echo 🌿 EcoVision - Setup de Modelos YOLO
echo =============================================
echo.

REM Verifica Python
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Python não encontrado!
    echo    Instale Python 3.8+ de python.org
    pause
    exit /b 1
)

echo ✓ Python encontrado

REM Verifica ultralytics
echo.
echo Verificando dependências...
python -c "import ultralytics" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ⚠️  ultralytics não instalado
    echo    Instalando...
    pip install ultralytics onnx
    echo ✓ ultralytics instalado
) else (
    echo ✓ ultralytics já instalado
)

REM Verifica pasta models
if not exist "models" (
    echo ⚠️  Pasta models não encontrada, criando...
    mkdir models
)

echo.
echo =============================================
echo Escolha uma opção:
echo =============================================
echo 1) Converter modelo .pt existente
echo 2) Baixar modelo pré-treinado COCO (teste)
echo 3) Verificar modelos instalados
echo 4) Sair
echo.
set /p option="Opção [1-4]: "

if "%option%"=="1" goto convert
if "%option%"=="2" goto download
if "%option%"=="3" goto check
if "%option%"=="4" goto end
echo ❌ Opção inválida
pause
exit /b 1

:convert
echo.
echo 📁 Modelos .pt em models/:
dir /b models\*.pt 2>nul || echo    (nenhum)
echo.
set /p pt_file="Digite o caminho do arquivo .pt: "

if not exist "%pt_file%" (
    echo ❌ Arquivo não encontrado: %pt_file%
    pause
    exit /b 1
)

echo.
echo 🔄 Convertendo %pt_file% para ONNX...
python convert_to_onnx.py "%pt_file%"

REM Move arquivo ONNX
for %%F in ("%pt_file%") do set "onnx_file=%%~dpnF.onnx"
if exist "%onnx_file%" (
    move /y "%onnx_file%" models\yolov8n.onnx >nul
    echo.
    echo ✅ Modelo convertido: models\yolov8n.onnx
)
goto next_steps

:download
echo.
echo ⚠️  ATENÇÃO: Modelo COCO tem 80 classes, não as 4 específicas
echo    Use apenas para teste!
echo.
set /p confirm="Continuar? [y/N]: "

if /i not "%confirm%"=="y" (
    echo Cancelado.
    goto end
)

echo.
echo 📥 Baixando YOLOv8n pré-treinado...
cd models
powershell -Command "Invoke-WebRequest -Uri 'https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt' -OutFile 'yolov8n.pt'"
cd ..

echo.
echo 🔄 Convertendo para ONNX...
python convert_to_onnx.py models\yolov8n.pt

if exist "yolov8n.onnx" (
    move /y yolov8n.onnx models\ >nul
    echo.
    echo ✅ Modelo de teste instalado: models\yolov8n.onnx
    echo ⚠️  Este modelo NÃO detecta materiais de reciclagem!
    echo    Treine um modelo próprio com 4 classes:
    echo    - papel (ID 0)
    echo    - metal (ID 1)
    echo    - plastico (ID 2)
    echo    - vidro (ID 3)
)
goto next_steps

:check
echo.
echo 📊 Status dos modelos:
echo.

if exist "models\yolov8n.onnx" (
    for %%F in ("models\yolov8n.onnx") do set size=%%~zF
    set /a size_mb=!size! / 1048576
    echo ✓ models\yolov8n.onnx (!size_mb!MB) - PRONTO!
) else (
    echo ✗ models\yolov8n.onnx - NÃO ENCONTRADO
)

echo.
echo Modelos .pt disponíveis:
dir /b models\*.pt 2>nul || echo   (nenhum)

echo.
echo Modelos .onnx disponíveis:
dir /b models\*.onnx 2>nul || echo   (nenhum)

echo.
pause
exit /b 0

:next_steps
echo.
echo =============================================
echo 📝 Próximos Passos:
echo =============================================
echo 1. Inicie o sistema:
echo    run_dev.bat
echo.
echo 2. Acesse http://localhost:5000
echo.
echo 3. Login e aba 'Monitor'
echo.
echo 4. 'Iniciar Sistema' e permita câmera
echo.
echo 5. ✅ Bounding boxes devem aparecer!
echo.
echo Console (F12) deve mostrar:
echo   [ONNX] ✅ Modelo carregado
echo   [INFERÊNCIA ONNX] X detecções...
echo.
echo =============================================

:end
pause
