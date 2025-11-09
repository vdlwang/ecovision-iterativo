# 📂 Estrutura do Projeto EcoVision

## 📋 Visão Geral

```
ecovision/
├── 📄 README.md                    # Documentação principal
├── 📄 PROJECT_GUIDE.md             # Guia do desenvolvedor
├── 📄 STRUCTURE.md                 # Este arquivo
├── 📄 App.tsx                      # Componente raiz React
│
├── 📁 components/                  # Componentes React
│   ├── AccuracyControl.tsx
│   ├── CameraFeed.tsx
│   ├── ConveyorSystem.tsx
│   ├── GateConfiguration.tsx
│   ├── Login.tsx
│   ├── MonitorPanel.tsx
│   ├── Sidebar.tsx
│   ├── StatisticsPanel.tsx
│   ├── UserProfile.tsx
│   ├── 📁 figma/
│   │   └── ImageWithFallback.tsx
│   └── 📁 ui/                      # Componentes Shadcn/UI
│       └── (45+ componentes)
│
├── 📁 supabase/
│   ├── 📁 functions/server/        # Edge Functions (Backend)
│   │   ├── index.tsx               # API principal (Hono)
│   │   ├── kv_store.tsx            # KV Store utility
│   │   ├── Atuador.tsx             # IAtuador + ControladorSerial
│   │   ├── Autenticacao.tsx        # Autenticação
│   │   ├── BancoDeDados.tsx        # Persistência
│   │   ├── Camera.tsx              # Captura
│   │   ├── Cancela.tsx             # Cancela
│   │   ├── Dashboard.tsx           # Visualização
│   │   ├── Esteira.tsx             # Esteira
│   │   ├── ModeloIA.tsx            # Modelo YOLO
│   │   ├── OutputData.tsx          # Detecção
│   │   ├── RegistroProcessamento.tsx
│   │   └── Usuario.tsx             # Usuário
│   └── 📁 migrations/
│       ├── 001_create_ecovision_tables.sql
│       └── README.md
│
├── 📁 diagrams/                    # Diagramas UML (PlantUML)
│   ├── INDEX.md
│   ├── README.md
│   ├── EXECUTIVE_SUMMARY.md
│   ├── QUICK_REFERENCE.md
│   ├── architecture-diagram.puml
│   ├── class-diagram.puml
│   ├── component-diagram.puml
│   ├── data-flow-diagram.puml
│   ├── database-diagram.puml
│   └── sequence-diagram.puml
│
├── 📁 models/                      # Modelos YOLO (.pt)
│   └── README.md
│
├── 📁 styles/
│   └── globals.css                 # Estilos + tokens
│
├── 📁 utils/
│   └── 📁 supabase/
│       ├── client.tsx              # Cliente Supabase
│       └── info.tsx                # Config do projeto
│
├── 📄 inference_server.py          # Servidor Python YOLO
├── 📄 requirements.txt             # Deps Python
├── 📄 test_setup.py               # Script de teste
├── 📄 run_dev.sh                  # Executar (Linux/Mac)
└── 📄 run_dev.bat                 # Executar (Windows)
```

## 🎯 Arquivos Principais

### Frontend

| Arquivo | Propósito |
|---------|-----------|
| `App.tsx` | Componente raiz, roteamento |
| `components/CameraFeed.tsx` | Captura webcam + detecções |
| `components/ConveyorSystem.tsx` | Animação esteira |
| `components/StatisticsPanel.tsx` | Dashboard com gráficos |
| `components/Login.tsx` | Autenticação Google |
| `styles/globals.css` | Paleta de cores e tokens |

### Backend

| Arquivo | Propósito |
|---------|-----------|
| `supabase/functions/server/index.tsx` | API REST (Hono) |
| `supabase/functions/server/kv_store.tsx` | KV Store |
| `supabase/functions/server/*.tsx` | Classes do domínio (separadas) |

### Python

| Arquivo | Propósito |
|---------|-----------|
| `inference_server.py` | FastAPI + YOLO |
| `requirements.txt` | Dependências |
| `test_setup.py` | Validar instalação |

### Documentação

| Arquivo | Propósito |
|---------|-----------|
| `README.md` | Documentação principal |
| `PROJECT_GUIDE.md` | Guia do desenvolvedor |
| `diagrams/INDEX.md` | Índice de diagramas |
| `diagrams/*.puml` | Diagramas UML |

## 🗂️ Organização por Funcionalidade

### Autenticação
- `components/Login.tsx`
- `supabase/functions/server/Autenticacao.tsx`
- `utils/supabase/client.tsx`

### Captura e Detecção
- `components/CameraFeed.tsx`
- `supabase/functions/server/Camera.tsx`
- `supabase/functions/server/ModeloIA.tsx`
- `inference_server.py`

### Controle da Esteira
- `components/ConveyorSystem.tsx`
- `components/GateConfiguration.tsx`
- `supabase/functions/server/Esteira.tsx`
- `supabase/functions/server/Cancela.tsx`
- `supabase/functions/server/Atuador.tsx`

### Dashboard e Estatísticas
- `components/StatisticsPanel.tsx`
- `components/MonitorPanel.tsx`
- `supabase/functions/server/Dashboard.tsx`
- `supabase/functions/server/BancoDeDados.tsx`

### Persistência
- `supabase/migrations/001_create_ecovision_tables.sql`
- `supabase/functions/server/kv_store.tsx`
- `supabase/functions/server/BancoDeDados.tsx`
- `supabase/functions/server/RegistroProcessamento.tsx`

## 🏗️ Arquitetura em Camadas

```
┌─────────────────────────────────────────┐
│          APRESENTAÇÃO (Frontend)         │
│  React + TypeScript + Tailwind + Shadcn │
│                                          │
│  components/                             │
│  ├── CameraFeed.tsx                     │
│  ├── ConveyorSystem.tsx                 │
│  ├── StatisticsPanel.tsx                │
│  └── ...                                 │
└─────────────────────────────────────────┘
                    ↕
┌─────────────────────────────────────────┐
│           APLICAÇÃO (Backend)            │
│     Supabase Edge Functions (Hono)      │
│                                          │
│  supabase/functions/server/             │
│  ├── index.tsx (API)                    │
│  └── *.tsx (Classes)                    │
└─────────────────────────────────────────┘
                    ↕
┌─────────────────────────────────────────┐
│          DOMÍNIO (Lógica de Negócio)    │
│                                          │
│  Classes separadas:                      │
│  ├── Camera, Esteira, Cancela          │
│  ├── ModeloIA, BancoDeDados             │
│  └── Dashboard, Autenticacao            │
└─────────────────────────────────────────┘
                    ↕
┌─────────────────────────────────────────┐
│        INFRAESTRUTURA (Dados + IA)      │
│                                          │
│  ├── PostgreSQL (Supabase)              │
│  ├── KV Store (Cache)                   │
│  └── Python YOLO (inference_server.py)  │
└─────────────────────────────────────────┘
```

## 📝 Convenções

### Nomenclatura

- **Componentes React:** PascalCase (`CameraFeed.tsx`)
- **Classes Backend:** PascalCase (`ModeloIA.tsx`)
- **Utilitários:** camelCase (`kv_store.tsx`)
- **Constantes:** UPPER_SNAKE_CASE

### Organização

- **1 componente por arquivo**
- **1 classe por arquivo** (backend)
- **Imports agrupados** por origem
- **Props tipadas** com interfaces/types

### Estilo

- **Tailwind CSS** para estilização
- **Shadcn/UI** para componentes
- **Lucide React** para ícones
- **Recharts** para gráficos

## 🎨 Paleta de Cores

Definida em `styles/globals.css`:

```css
/* Verde EcoVision */
--eco-green-dark: #034732;
--eco-green-light: #abf2ab;

/* Materiais */
--material-papel: #163b6f;    /* Azul */
--material-metal: #196626;    /* Verde */
--material-plastico: #dc1f2e; /* Vermelho vibrante */
--material-vidro: #d2b91f;    /* Amarelo */
```

## 🔗 Dependências Principais

### Frontend
- React 18
- TypeScript
- Tailwind CSS v4
- Shadcn/UI
- Recharts
- Lucide React
- Supabase JS Client

### Backend
- Deno
- Hono
- Supabase (PostgreSQL + Auth)

### Python
- FastAPI
- Ultralytics YOLO
- OpenCV
- PyTorch

---

**EcoVision** - Sistema de Reciclagem Inteligente 🌱♻️
