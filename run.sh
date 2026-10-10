#!/bin/bash

echo "========================================"
echo " EcoVision - Inicializacao Completa"
echo "========================================"
echo ""

# Verificar se Python esta instalado
if ! command -v python3 &> /dev/null; then
    echo "[ERRO] Python nao encontrado. Instale Python 3.8+"
    exit 1
fi

# Verificar se Node esta instalado
if ! command -v node &> /dev/null; then
    echo "[ERRO] Node.js nao encontrado. Instale Node.js 16+"
    exit 1
fi

echo "[1/3] Iniciando Backend Python..."
cd backend
gnome-terminal -- bash -c "python3 ecovision_local_modf.py; exec bash" || \
xterm -e "python3 ecovision_local_modf.py" || \
python3 ecovision_local_modf.py &
cd ..
sleep 3

echo "[2/3] Iniciando Frontend React..."
cd frontend
gnome-terminal -- bash -c "npm run dev; exec bash" || \
xterm -e "npm run dev" || \
npm run dev &
cd ..
sleep 2

echo "[3/3] Sistema iniciado!"
echo ""
echo "Backend: Python rodando em ws://localhost:8765"
echo "Frontend: React rodando em http://localhost:5173"
echo ""
echo "Abrindo navegador..."
sleep 1

# Abrir navegador
xdg-open http://localhost:5173 2>/dev/null || \
open http://localhost:5173 2>/dev/null || \
echo "Abra manualmente: http://localhost:5173"
