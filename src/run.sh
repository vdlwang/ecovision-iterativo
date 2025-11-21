#!/bin/bash

echo "========================================"
echo "EcoVision - Sistema de Reciclagem"
echo "========================================"
echo ""

echo "[1/2] Iniciando Backend Python..."
cd backend
python3 ecovision_local.py &
BACKEND_PID=$!

echo "[2/2] Frontend React já está rodando no Figma Make"
echo ""
echo "========================================"
echo "Sistema iniciado!"
echo "========================================"
echo ""
echo "Backend: http://localhost:8765"
echo "Frontend: Verifique o Figma Make"
echo ""
echo "Pressione Ctrl+C para encerrar..."

# Aguarda Ctrl+C
trap "kill $BACKEND_PID; exit" INT
wait
