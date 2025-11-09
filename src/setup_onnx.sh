#!/bin/bash
# EcoVision - Setup Simplificado para Modo ONNX
# Este script configura o sistema para usar inferência local no navegador

set -e

echo "============================================================"
echo "🌿 EcoVision - Setup Modo ONNX (Inferência Local)"
echo "============================================================"
echo ""

# Verifica se Python está instalado
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "❌ Erro: Python não encontrado"
    echo "   Instale Python 3.8+ de https://www.python.org"
    exit 1
fi

PYTHON_CMD=$(command -v python3 || command -v python)
echo "✅ Python encontrado: $PYTHON_CMD"

# Verifica se Ultralytics está instalado
echo ""
echo "📦 Verificando dependências..."
if ! $PYTHON_CMD -c "import ultralytics" 2>/dev/null; then
    echo "⚠️  ultralytics não encontrado, instalando..."
    $PYTHON_CMD -m pip install ultralytics --quiet
    echo "✅ ultralytics instalado"
else
    echo "✅ ultralytics já instalado"
fi

# Verifica se existe modelo .pt
echo ""
echo "🔍 Procurando modelo YOLO..."

MODEL_PT=""
if [ -f "models/yolov8n.pt" ]; then
    MODEL_PT="models/yolov8n.pt"
elif [ -f "models/best.pt" ]; then
    MODEL_PT="models/best.pt"
elif [ -f "best.pt" ]; then
    MODEL_PT="best.pt"
elif [ -f "yolov8n.pt" ]; then
    MODEL_PT="yolov8n.pt"
fi

if [ -z "$MODEL_PT" ]; then
    echo "⚠️  Nenhum modelo .pt encontrado nas seguintes localizações:"
    echo "   - models/yolov8n.pt"
    echo "   - models/best.pt"
    echo "   - best.pt"
    echo "   - yolov8n.pt"
    echo ""
    echo "📥 Baixando YOLOv8n pré-treinado..."
    $PYTHON_CMD -c "from ultralytics import YOLO; YOLO('yolov8n.pt')" 2>/dev/null || true
    
    # Procura novamente após download
    if [ -f "yolov8n.pt" ]; then
        MODEL_PT="yolov8n.pt"
    else
        echo ""
        echo "❌ Falha ao baixar modelo automaticamente"
        echo "   Por favor, baixe manualmente ou treine seu modelo"
        echo "   Veja: models/README.md para mais informações"
        exit 1
    fi
fi

echo "✅ Modelo encontrado: $MODEL_PT"

# Verifica se já existe modelo ONNX
if [ -f "models/yolov8n.onnx" ]; then
    echo ""
    echo "⚠️  Modelo ONNX já existe: models/yolov8n.onnx"
    read -p "   Deseja reconverter? (s/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        echo "✅ Usando modelo ONNX existente"
        echo ""
        echo "============================================================"
        echo "✅ Setup concluído!"
        echo "============================================================"
        echo ""
        echo "📋 Próximos passos:"
        echo "   1. npm install       # Instalar dependências Node"
        echo "   2. npm run dev       # Iniciar aplicação"
        echo "   3. Abrir navegador em http://localhost:5173"
        echo ""
        echo "🎯 O sistema usará inferência ONNX automaticamente!"
        exit 0
    fi
fi

# Converte modelo
echo ""
echo "🔄 Convertendo modelo para ONNX..."
echo "   Entrada: $MODEL_PT"
echo "   Saída: models/yolov8n.onnx"

$PYTHON_CMD convert_to_onnx.py "$MODEL_PT" --output yolov8n.onnx

# Move para pasta models se necessário
if [ -f "yolov8n.onnx" ] && [ ! -f "models/yolov8n.onnx" ]; then
    echo ""
    echo "📁 Movendo modelo para pasta models/..."
    mkdir -p models
    mv yolov8n.onnx models/
    echo "✅ Modelo movido para models/yolov8n.onnx"
fi

# Verifica tamanho do arquivo
if [ -f "models/yolov8n.onnx" ]; then
    SIZE=$(du -h "models/yolov8n.onnx" | cut -f1)
    echo ""
    echo "✅ Conversão concluída!"
    echo "   Arquivo: models/yolov8n.onnx"
    echo "   Tamanho: $SIZE"
fi

echo ""
echo "============================================================"
echo "✅ Setup concluído com sucesso!"
echo "============================================================"
echo ""
echo "📋 Próximos passos:"
echo "   1. npm install       # Instalar dependências Node (se ainda não fez)"
echo "   2. npm run dev       # Iniciar aplicação"
echo "   3. Abrir navegador em http://localhost:5173"
echo ""
echo "🎯 O sistema detectará o modelo ONNX automaticamente e usará"
echo "   inferência local no navegador (sem servidor Python necessário)!"
echo ""
echo "📖 Documentação:"
echo "   - QUICKSTART_ONNX.md     # Guia rápido"
echo "   - INFERENCE_MODES.md     # Comparação de modos"
echo "   - models/README.md       # Treinamento de modelos"
echo ""
