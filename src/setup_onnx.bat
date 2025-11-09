@echo off
REM EcoVision - Setup Simplificado para Modo ONNX
REM Este script configura o sistema para usar inferência local no navegador

echo ============================================================
echo 🌿 EcoVision - Setup Modo ONNX (Inferência Local)
echo ============================================================
echo.

REM Verifica se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Erro: Python não encontrado
    echo    Instale Python 3.8+ de https://www.python.org
    pause
    exit /b 1
)
echo ✅ Python encontrado

REM Verifica se Ultralytics está instalado
echo.
echo 📦 Verificando dependências...
python -c "import ultralytics" 2>nul
if errorlevel 1 (
    echo ⚠️  ultralytics não encontrado, instalando...
    python -m pip install ultralytics --quiet
    echo ✅ ultralytics instalado
) else (
    echo ✅ ultralytics já instalado
)

REM Verifica se existe modelo .pt
echo.
echo 🔍 Procurando modelo YOLO...

set MODEL_PT=
if exist "models\yolov8n.pt" set MODEL_PT=models\yolov8n.pt
if exist "models\best.pt" set MODEL_PT=models\best.pt
if exist "best.pt" set MODEL_PT=best.pt
if exist "yolov8n.pt" set MODEL_PT=yolov8n.pt

if not defined MODEL_PT (
    echo ⚠️  Nenhum modelo .pt encontrado nas seguintes localizações:
    echo    - models\yolov8n.pt
    echo    - models\best.pt
    echo    - best.pt
    echo    - yolov8n.pt
    echo.
    echo 📥 Baixando YOLOv8n pré-treinado...
    python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')" 2>nul
    
    if exist "yolov8n.pt" (
        set MODEL_PT=yolov8n.pt
    ) else (
        echo.
        echo ❌ Falha ao baixar modelo automaticamente
        echo    Por favor, baixe manualmente ou treine seu modelo
        echo    Veja: models\README.md para mais informações
        pause
        exit /b 1
    )
)

echo ✅ Modelo encontrado: %MODEL_PT%

REM Verifica se já existe modelo ONNX
if exist "models\yolov8n.onnx" (
    echo.
    echo ⚠️  Modelo ONNX já existe: models\yolov8n.onnx
    set /p RECONVERT="   Deseja reconverter? (s/N): "
    if /i not "%RECONVERT%"=="s" (
        echo ✅ Usando modelo ONNX existente
        goto :finish
    )
)

REM Converte modelo
echo.
echo 🔄 Convertendo modelo para ONNX...
echo    Entrada: %MODEL_PT%
echo    Saída: models\yolov8n.onnx

python convert_to_onnx.py "%MODEL_PT%" --output yolov8n.onnx

REM Move para pasta models se necessário
if exist "yolov8n.onnx" (
    if not exist "models\yolov8n.onnx" (
        echo.
        echo 📁 Movendo modelo para pasta models\...
        if not exist "models" mkdir models
        move yolov8n.onnx models\ >nul
        echo ✅ Modelo movido para models\yolov8n.onnx
    )
)

REM Verifica tamanho do arquivo
if exist "models\yolov8n.onnx" (
    for %%A in ("models\yolov8n.onnx") do set SIZE=%%~zA
    set /a SIZE_MB=%SIZE% / 1048576
    echo.
    echo ✅ Conversão concluída!
    echo    Arquivo: models\yolov8n.onnx
    echo    Tamanho: ~%SIZE_MB% MB
)

:finish
echo.
echo ============================================================
echo ✅ Setup concluído com sucesso!
echo ============================================================
echo.
echo 📋 Próximos passos:
echo    1. npm install       # Instalar dependências Node (se ainda não fez)
echo    2. npm run dev       # Iniciar aplicação
echo    3. Abrir navegador em http://localhost:5173
echo.
echo 🎯 O sistema detectará o modelo ONNX automaticamente e usará
echo    inferência local no navegador (sem servidor Python necessário)!
echo.
echo 📖 Documentação:
echo    - QUICKSTART_ONNX.md     # Guia rápido
echo    - INFERENCE_MODES.md     # Comparação de modos
echo    - models\README.md       # Treinamento de modelos
echo.
pause
