#!/bin/bash

# EcoVision - Setup Automático de Modelos YOLO
# Este script facilita a conversão e instalação de modelos

set -e  # Para na primeira falha

echo "============================================="
echo "🌿 EcoVision - Setup de Modelos YOLO"
echo "============================================="
echo ""

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Verifica Python
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo -e "${RED}❌ Python não encontrado!${NC}"
    echo "   Instale Python 3.8+ e tente novamente"
    exit 1
fi

PYTHON_CMD=$(command -v python3 || command -v python)
echo -e "${GREEN}✓${NC} Python encontrado: $PYTHON_CMD"

# Verifica ultralytics
echo ""
echo "Verificando dependências..."
if ! $PYTHON_CMD -c "import ultralytics" 2>/dev/null; then
    echo -e "${YELLOW}⚠️${NC}  ultralytics não instalado"
    echo "   Instalando..."
    pip install ultralytics onnx
    echo -e "${GREEN}✓${NC} ultralytics instalado"
else
    echo -e "${GREEN}✓${NC} ultralytics já instalado"
fi

# Verifica pasta models
if [ ! -d "models" ]; then
    echo -e "${YELLOW}⚠️${NC}  Pasta models não encontrada, criando..."
    mkdir -p models
fi

echo ""
echo "============================================="
echo "Escolha uma opção:"
echo "============================================="
echo "1) Converter modelo .pt existente"
echo "2) Baixar modelo pré-treinado COCO (apenas para teste)"
echo "3) Verificar modelos instalados"
echo "4) Sair"
echo ""
read -p "Opção [1-4]: " option

case $option in
    1)
        echo ""
        echo "📁 Modelos .pt encontrados em models/:"
        ls -1 models/*.pt 2>/dev/null || echo "   (nenhum)"
        echo ""
        read -p "Digite o caminho do arquivo .pt: " pt_file
        
        if [ ! -f "$pt_file" ]; then
            echo -e "${RED}❌ Arquivo não encontrado: $pt_file${NC}"
            exit 1
        fi
        
        echo ""
        echo "🔄 Convertendo $pt_file para ONNX..."
        $PYTHON_CMD convert_to_onnx.py "$pt_file"
        
        # Move arquivo ONNX para models/
        onnx_file="${pt_file%.pt}.onnx"
        if [ -f "$onnx_file" ]; then
            mv "$onnx_file" models/yolov8n.onnx
            echo ""
            echo -e "${GREEN}✅ Modelo convertido e movido para models/yolov8n.onnx${NC}"
        fi
        ;;
    
    2)
        echo ""
        echo -e "${YELLOW}⚠️  ATENÇÃO:${NC} O modelo COCO tem 80 classes, não as 4 específicas."
        echo "   Use apenas para teste. Para produção, treine seu próprio modelo!"
        echo ""
        read -p "Continuar? [y/N]: " confirm
        
        if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
            echo "Cancelado."
            exit 0
        fi
        
        echo ""
        echo "📥 Baixando YOLOv8n pré-treinado..."
        
        cd models
        wget -q --show-progress https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt
        cd ..
        
        echo ""
        echo "🔄 Convertendo para ONNX..."
        $PYTHON_CMD convert_to_onnx.py models/yolov8n.pt
        
        if [ -f "yolov8n.onnx" ]; then
            mv yolov8n.onnx models/
            echo ""
            echo -e "${GREEN}✅ Modelo de teste instalado em models/yolov8n.onnx${NC}"
            echo -e "${YELLOW}⚠️  Lembre-se: este modelo NÃO detecta materiais de reciclagem!${NC}"
            echo "   Você deve treinar um modelo próprio com 4 classes:"
            echo "   - papel (ID 0)"
            echo "   - metal (ID 1)"
            echo "   - plastico (ID 2)"
            echo "   - vidro (ID 3)"
        fi
        ;;
    
    3)
        echo ""
        echo "📊 Status dos modelos:"
        echo ""
        
        if [ -f "models/yolov8n.onnx" ]; then
            size=$(ls -lh models/yolov8n.onnx | awk '{print $5}')
            echo -e "${GREEN}✓${NC} models/yolov8n.onnx ($size) - PRONTO PARA USO!"
        else
            echo -e "${RED}✗${NC} models/yolov8n.onnx - NÃO ENCONTRADO"
        fi
        
        echo ""
        echo "Modelos .pt disponíveis:"
        ls -lh models/*.pt 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}' || echo "  (nenhum)"
        
        echo ""
        echo "Modelos .onnx disponíveis:"
        ls -lh models/*.onnx 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}' || echo "  (nenhum)"
        ;;
    
    4)
        echo "Saindo..."
        exit 0
        ;;
    
    *)
        echo -e "${RED}❌ Opção inválida${NC}"
        exit 1
        ;;
esac

echo ""
echo "============================================="
echo "📝 Próximos Passos:"
echo "============================================="
echo "1. Inicie o sistema:"
echo "   ./run_dev.sh"
echo ""
echo "2. Acesse http://localhost:5000"
echo ""
echo "3. Faça login e vá para aba 'Monitor'"
echo ""
echo "4. Clique em 'Iniciar Sistema'"
echo ""
echo "5. Permita acesso à câmera"
echo ""
echo "6. ✅ Bounding boxes devem aparecer!"
echo ""
echo "Console do navegador (F12) deve mostrar:"
echo "  [ONNX] ✅ Modelo carregado com sucesso"
echo "  [INFERÊNCIA ONNX] X detecção(ões)..."
echo ""
echo "============================================="
