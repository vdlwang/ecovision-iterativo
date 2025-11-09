# 🌿 EcoVision - Sistema Inteligente de Reciclagem com IA

<div align="center">

![EcoVision](https://img.shields.io/badge/EcoVision-Sistema%20de%20Reciclagem-008148?style=for-the-badge&logo=recycle)
![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white)
![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![YOLO](https://img.shields.io/badge/YOLOv8-00FFFF?style=for-the-badge&logo=yolo&logoColor=black)

**Sistema de controle para esteira de reciclagem integrado com IA para detecção e separação automática de materiais recicláveis**

[🏗️ Arquitetura](#️-arquitetura) • [📊 Diagramas](./diagrams/INDEX.md) • [🚀 Deploy](#-deploy-em-produção)

</div>

---

## 📋 Sobre o Projeto

O **EcoVision** é um sistema completo de controle para centros de reciclagem que utiliza **visão computacional** e **inteligência artificial** para automatizar a separação de materiais recicláveis em tempo real.

### 🎥 Como Funciona

1. **Câmera** captura imagens da esteira em movimento
2. **IA (YOLO)** detecta e classifica materiais (papel, metal, plástico, vidro)
3. **Sistema** aciona cancelas automaticamente para separar cada material
4. **Dashboard** monitora estatísticas e performance em tempo real

### 🌟 Diferenciais

- ✅ **Detecção em Tempo Real** com webcam/câmera
- ✅ **3 Modelos YOLO** (nano, small, medium) para diferentes necessidades
- ✅ **Configurável** - defina qual cancela separa qual material
- ✅ **Banco de Dados Real** - todas detecções persistidas no PostgreSQL
- ✅ **Dashboard Completo** - gráficos e métricas em tempo real
- ✅ **Autenticação Google** - login seguro via Supabase Auth
- ✅ **Código Open Source** - MIT License

---

## 🚀 Quick Start

### ⚡ 3 Passos para Rodar o Projeto

```bash
# 1. Instalar dependências Python
pip install -r requirements.txt

# 2. Baixar modelos YOLO (coloque na pasta models/)
# Download: https://github.com/ultralytics/assets/releases
# Ou deixe baixar automaticamente na primeira execução

# 3. Executar o sistema
./run_dev.sh          # Linux/Mac
# ou
run_dev.bat           # Windows
```

**Pronto!** Acesse **http://localhost:5173** (frontend) e configure o backend no Supabase.

### 📋 Requisitos

- **Python 3.8+** - Para servidor de inferência
- **Node.js 18+** - Para frontend React
- **Webcam** (integrada ou USB)
- **8GB RAM** mínimo (16GB recomendado)
- **HTTPS** (produção) ou localhost (desenvolvimento)

### ✅ Onde Funciona

| Ambiente | Câmera | Inferência | Status |
|----------|--------|------------|--------|
| **Localhost** (HTTP) | ✅ | ✅ | **100% Funcional** |
| **Produção** (HTTPS) | ✅ | ✅ | **100% Funcional** |
| **Playground Figma** | ⚠️ | ⚠️ | Limitado (CORS/Câmera) |

**⚠️ IMPORTANTE:** 
- ✅ O sistema é **totalmente funcional** quando executado localmente ou em produção com HTTPS
- ✅ Captura frames da webcam → Envia para YOLO → Retorna bounding boxes na tela
- ⚠️ O Playground do Figma tem limitações de segurança que podem bloquear a câmera
- 🚀 Para testes reais, execute localmente com `./run_dev.sh`

**📹 Como funciona a câmera:**
1. Faça login no sistema (Google OAuth)
2. Navegador solicita permissão de câmera automaticamente
3. Clique em "Permitir" no popup do navegador
4. Clique em "Iniciar Sistema" no feed da câmera
5. Pronto! Sistema começa a detectar automaticamente

**🔧 Problemas com permissão de câmera?**
- Chrome: `chrome://settings/content/camera`
- Firefox: Ícone de cadeado → Permissões → Câmera
- Edge: Ícone de cadeado → Permissões do site
- Safari: Preferências → Sites → Câmera

---

## 🎯 Funcionalidades

### 🖥️ Interface do Usuário

#### 1. Monitor
- Visualização da webcam em tempo real
- Bounding boxes coloridos nas detecções
- Animação da esteira rolante
- Estado das 3 cancelas (aberta/fechada)
- Lista de detecções recentes com confiança

#### 2. Configuração de Cancelas
- Configure qual material cada cancela irá separar
- Teste manual de acionamento
- Visualização do status atual

#### 3. Controle de Modelo
- Escolha entre YOLOv8n, YOLOv8s, YOLOv8m
- Ajuste a confiança mínima (0-100%)
- Informações sobre cada modelo

#### 4. Dashboard
- **Dados Reais do Banco PostgreSQL**
- Gráficos de pizza: Distribuição por material
- Gráficos de barras: Acionamentos por cancela
- Métricas: Total processado, confiança média
- Lista de detecções recentes
- Atualização automática a cada 30s

#### 5. Perfil
- Informações do usuário
- Histórico de sessões
- Estatísticas pessoais

### 🤖 IA e Detecção

#### Materiais Detectados
| Material | Cor | Exemplos |
|----------|-----|----------|
| 📄 **Papel** | Azul (#163b6f) | Livros, jornais, papelão |
| 🥫 **Metal** | Verde (#196626) | Latas, talheres, alumínio |
| 🍾 **Plástico** | Vermelho vibrante (#dc1f2e) | Garrafas PET, copos, sacolas |
| 🍷 **Vidro** | Amarelo (#d2b91f) | Garrafas, copos, frascos |

#### Modelos Disponíveis
- **YOLOv8n** (nano): 6MB, ~100 FPS, ideal para tempo real
- **YOLOv8s** (small): 22MB, ~50 FPS, balanceado
- **YOLOv8m** (medium): 52MB, ~25 FPS, máxima precisão

---

## 🏗️ Arquitetura

### Stack Tecnológico

#### Frontend
```
React + TypeScript + Tailwind CSS
├── Camera Feed: getUserMedia API (webcam)
├── UI Components: Shadcn/UI
├── Charts: Recharts
├── Icons: Lucide React
└── Auth: Supabase Auth (Google OAuth)
```

#### Backend
```
Supabase Edge Functions (Deno + Hono)
├── PostgreSQL: Banco de dados
├── Row Level Security: Segurança por usuário
├── Real-time: Atualização em tempo real
└── KV Store: Cache e configurações
```

#### IA/ML
```
Python + FastAPI + Ultralytics YOLO
├── OpenCV: Processamento de imagem
├── PyTorch: Backend de ML
├── Base64: Transmissão de imagens
└── CUDA: Aceleração GPU (opcional)
```

### Fluxo de Dados

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐      ┌──────────────┐
│             │      │              │      │             │      │              │
│   Webcam    │─────▶│   Frontend   │─────▶│   Backend   │─────▶│   Python     │
│  (Camera)   │      │   (React)    │      │  (Supabase) │      │   (YOLO)     │
│             │      │              │      │             │      │              │
└─────────────┘      └──────────────┘      └──────────────┘      └──────────────┘
                             │                     │
                             │                     ▼
                             │              ┌──────────────┐
                             │              │              │
                             └─────────────▶│  PostgreSQL  │
                                            │  (Database)  │
                                            │              │
                                            └──────────────┘

1. Webcam captura frame a cada 2s
2. Frontend converte para base64
3. Backend autentica usuário (OAuth/Demo)
4. Python processa com YOLO
5. Backend salva no PostgreSQL
6. Frontend renderiza bounding boxes
7. Dashboard atualiza estatísticas
```

**📊 Diagramas completos:** [diagrams/INDEX.md](./diagrams/INDEX.md)

---

## 📊 Banco de Dados

### Tabelas Principais

```sql
-- Detecções da IA
inferences
├── id (UUID)
├── user_id (UUID)
├── material_detected (TEXT)      -- papel, metal, plastico, vidro
├── confidence (DECIMAL)           -- 0.00 - 100.00
├── gate_number (INTEGER)          -- 1, 2, 3
├── gate_activated (BOOLEAN)
├── model_version (TEXT)           -- YOLOv8n, YOLOv8s, YOLOv8m
├── processing_time_ms (INTEGER)
├── bounding_box (JSONB)
└── timestamp (TIMESTAMPTZ)

-- Sessões de usuário
user_sessions
├── id (UUID)
├── user_id (UUID)
├── started_at (TIMESTAMPTZ)
├── ended_at (TIMESTAMPTZ)
└── inferences_count (INTEGER)

-- Configuração do sistema
system_config
├── id (UUID)
├── user_id (UUID)
├── gate_1_material (TEXT)
├── gate_2_material (TEXT)
├── gate_3_material (TEXT)
├── min_confidence (INTEGER)       -- 0-100
└── model_version (TEXT)
```

**📖 Schema completo:** [supabase/migrations/001_create_ecovision_tables.sql](./supabase/migrations/001_create_ecovision_tables.sql)

---

## 📁 Estrutura do Projeto

```
ecovision/
├── 📁 components/           # Componentes React
│   ├── AccuracyControl.tsx  # Controle de confiança mínima
│   ├── CameraFeed.tsx       # Feed de webcam com detecções
│   ├── ConveyorSystem.tsx   # Animação da esteira
│   ├── GateConfiguration.tsx# Configuração das cancelas
│   ├── Login.tsx            # Tela de login
│   ├── MonitorPanel.tsx     # Painel de monitoramento
│   ├── Sidebar.tsx          # Menu lateral
│   ├── StatisticsPanel.tsx  # Dashboard de estatísticas
│   ├── UserProfile.tsx      # Perfil do usuário
│   └── 📁 ui/               # Componentes Shadcn/UI
│
├── 📁 supabase/
│   └── 📁 functions/server/ # Edge Functions
│       ├── index.tsx        # API principal (Hono)
│       ├── kv_store.tsx     # Utilitário KV Store
│       ├── Camera.tsx       # Classe Camera
│       ├── Usuario.tsx      # Classe Usuario
│       ├── OutputData.tsx   # Classe OutputData
│       ├── Atuador.tsx      # Interface IAtuador + ControladorSerial
│       ├── Esteira.tsx      # Classe Esteira
│       ├── Cancela.tsx      # Classe Cancela
│       ├── RegistroProcessamento.tsx
│       ├── BancoDeDados.tsx # Classe BancoDeDados
│       ├── ModeloIA.tsx     # Classe ModeloIA
│       ├── Dashboard.tsx    # Classe Dashboard
│       └── Autenticacao.tsx # Classe Autenticacao
│
├── 📁 diagrams/             # Diagramas UML (PlantUML)
│   ├── INDEX.md             # Índice dos diagramas
│   ├── architecture-diagram.puml
│   ├── class-diagram.puml
│   ├── component-diagram.puml
│   ├── data-flow-diagram.puml
│   ├── database-diagram.puml
│   └── sequence-diagram.puml
│
├── 📁 models/               # Modelos YOLO (.pt)
│   └── README.md
│
├── 📁 styles/               # Estilos globais
│   └── globals.css          # Paleta de cores e tokens
│
├── 📁 utils/                # Utilitários
│   └── supabase/
│       ├── client.tsx       # Cliente Supabase
│       └── info.tsx         # Config do projeto
│
├── App.tsx                  # Componente principal
├── inference_server.py      # Servidor Python de inferência YOLO
├── requirements.txt         # Dependências Python
├── run_dev.sh              # Script de execução (Linux/Mac)
├── run_dev.bat             # Script de execução (Windows)
├── test_setup.py           # Script de teste de instalação
└── README.md               # Este arquivo
```

---

## 🧪 Testes

### Testar Servidor Python

```bash
# Health check
curl http://localhost:8000/health

# Listar modelos disponíveis
curl http://localhost:8000/models

# Teste de inferência com imagem
curl -X POST http://localhost:8000/inference/file \
  -F "file=@test.jpg" \
  -F "model_version=YOLOv8n"
```

### Testar Frontend

1. Acesse http://localhost:5173
2. Faça login com Google ou use modo demo
3. Vá para "Monitor"
4. Permita acesso à webcam
5. Clique em "Iniciar Sistema"
6. Coloque objetos recicláveis na frente da câmera

**Esperado:** Bounding boxes aparecem em tempo real, detecções são listadas, estatísticas são atualizadas.

---

## 📈 Performance

### Benchmarks

| Componente | Métrica | Valor |
|------------|---------|-------|
| Webcam Capture | FPS | 30 |
| YOLOv8n (CPU) | Inferência | 100-500ms |
| YOLOv8n (GPU) | Inferência | 10-50ms |
| Backend API | Latência | <100ms |
| Dashboard Update | Intervalo | 30s |

### Requisitos de Hardware

#### Mínimo (CPU apenas)
- Intel i5 / Ryzen 5
- 8GB RAM
- Webcam HD (720p)
- **FPS esperado:** 20-40 (YOLOv8n)

#### Recomendado (com GPU)
- Intel i7 / Ryzen 7
- 16GB RAM
- NVIDIA GTX 1060+ (CUDA)
- Webcam Full HD (1080p)
- **FPS esperado:** 60-120 (YOLOv8n)

---

## 🚀 Deploy em Produção

### Servidor Python

**Opções:**
- [Render.com](https://render.com) (Free tier disponível)
- [Railway.app](https://railway.app)
- [Heroku](https://heroku.com)
- VPS (DigitalOcean, AWS EC2, etc)

**Exemplo Render:**
```yaml
# render.yaml
services:
  - type: web
    name: ecovision-inference
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python inference_server.py
```

### Frontend

**Opções:**
- [Vercel](https://vercel.com) (Recomendado)
- [Netlify](https://netlify.com)
- Figma Make (já deployado)

### Backend (Supabase)

Já está deployado! Configure apenas:
```bash
# No Supabase Dashboard → Project Settings → Edge Functions → Secrets
INFERENCE_SERVER_URL=https://seu-servidor.com
```

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Para contribuir:

1. Fork o projeto
2. Crie uma branch: `git checkout -b feature/nova-feature`
3. Commit suas mudanças: `git commit -m 'Adiciona nova feature'`
4. Push para a branch: `git push origin feature/nova-feature`
5. Abra um Pull Request

### Áreas que precisam de ajuda

- [ ] Treinar modelos YOLO customizados para reciclagem
- [ ] Implementar suporte para mais materiais (eletrônicos, orgânicos)
- [ ] Integração com hardware ESP32/Arduino
- [ ] Melhorias de performance
- [ ] Testes automatizados
- [ ] Tradução para outros idiomas

---

## 📝 Licença

Este projeto está sob a licença **MIT**. Veja o arquivo [LICENSE](./LICENSE) para mais detalhes.

```
MIT License - Copyright (c) 2025 EcoVision

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction...
```

---

## 🙏 Agradecimentos

- **Ultralytics** - Framework YOLO v8
- **Supabase** - Backend-as-a-Service
- **Shadcn/UI** - Componentes de interface
- **Comunidade Open Source** - Inspiração e suporte

---

## 📞 Suporte

**Problemas com o sistema?**

1. Verifique se o servidor Python está rodando: `curl http://localhost:8000/health`
2. Verifique se a câmera tem permissões no navegador
3. Verifique os logs do console do navegador (F12)
4. Consulte os [diagramas](./diagrams/INDEX.md) para entender a arquitetura

**Problemas com a câmera?**
- Navegador bloqueou? Veja configurações em `chrome://settings/content/camera`
- HTTPS obrigatório? Execute localmente ou use ngrok
- Dispositivo não encontrado? Verifique se a webcam está conectada

**Perguntas?** Abra uma [Issue](https://github.com/seu-usuario/ecovision/issues)

---

<div align="center">

**Desenvolvido com 💚 para um planeta mais sustentável**

![Reciclagem](https://img.shields.io/badge/♻️-Recicle-green?style=for-the-badge)

</div>
