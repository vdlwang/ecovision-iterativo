#!/bin/bash

# EcoVision - Script de Desenvolvimento
# Inicia todos os serviços necessários para desenvolvimento local

set -e

# Cores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_header() {
    echo ""
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Banner
clear
echo -e "${GREEN}"
cat << "EOF"
  ______          __     ___     _             
 |  ____|        / /    / (_)   (_)            
 | |__   ___ ___\ \   / / _ ___ _  ___  _ __  
 |  __| / __/ _ \\ \ / / | / __| |/ _ \| '_ \ 
 | |___| (_| (_) / / |/ /| \__ | | (_) | | | |
 |______\___\___/_/   \/ |_|___|_|\___/|_| |_|
                                               
  Sistema de Reciclagem Inteligente com IA    
EOF
echo -e "${NC}"

print_header "Verificando Ambiente"

# Verificar Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    print_success "Python instalado: $PYTHON_VERSION"
else
    print_error "Python 3 não encontrado!"
    exit 1
fi

# Verificar Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    print_success "Node.js instalado: $NODE_VERSION"
else
    print_error "Node.js não encontrado!"
    exit 1
fi

# Verificar ambiente virtual
if [ ! -d "venv" ]; then
    print_warning "Ambiente virtual não encontrado. Criando..."
    python3 -m venv venv
    print_success "Ambiente virtual criado!"
fi

# Ativar ambiente virtual
print_header "Ativando Ambiente Virtual"
source venv/bin/activate
print_success "Ambiente virtual ativado"

# Instalar dependências Python se necessário
if ! python -c "import ultralytics" &> /dev/null; then
    print_header "Instalando Dependências Python"
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    print_success "Dependências Python instaladas"
else
    print_success "Dependências Python já instaladas"
fi

# Verificar instalação
print_header "Executando Verificação de Sistema"
python test_setup.py

# Perguntar se deseja continuar
echo ""
read -p "Iniciar servidores? (s/N) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    print_warning "Abortado pelo usuário"
    exit 0
fi

# Criar pasta de logs
mkdir -p logs

# Função para cleanup ao sair
cleanup() {
    print_header "Encerrando Servidores"
    print_warning "Parando processos..."
    kill $(jobs -p) 2>/dev/null
    deactivate 2>/dev/null
    print_success "Servidores encerrados"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Iniciar servidor Python
print_header "Iniciando Servidor de Inferência Python"
python inference_server.py > logs/inference.log 2>&1 &
PYTHON_PID=$!
print_success "Servidor Python iniciado (PID: $PYTHON_PID)"
print_warning "Logs: tail -f logs/inference.log"

# Aguardar servidor iniciar
echo "Aguardando servidor Python inicializar..."
sleep 5

# Verificar se servidor está rodando
if curl -s http://localhost:8000/health > /dev/null; then
    print_success "Servidor Python está respondendo!"
else
    print_error "Servidor Python não está respondendo"
    print_warning "Verifique os logs: cat logs/inference.log"
    cleanup
fi

# Informações úteis
print_header "Servidores em Execução"
echo ""
echo -e "${GREEN}🐍 Servidor Python (Inferência):${NC}"
echo "   URL: http://localhost:8000"
echo "   Docs: http://localhost:8000/docs"
echo "   Logs: tail -f logs/inference.log"
echo ""
echo -e "${BLUE}📝 Para iniciar o frontend:${NC}"
echo "   npm run dev"
echo ""
echo -e "${YELLOW}⚡ Para parar os servidores:${NC}"
echo "   Pressione Ctrl+C"
echo ""

print_header "Sistema Pronto!"
print_success "Aguardando requisições..."
echo ""

# Manter script rodando
wait $PYTHON_PID
