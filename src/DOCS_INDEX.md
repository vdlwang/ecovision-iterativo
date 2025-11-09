# 📚 Índice de Documentação - EcoVision

## 🚀 Para Começar Rápido

| Arquivo | Quando Usar | Tempo |
|---------|-------------|-------|
| **[⚡ START.md](./START.md)** | Só quer os comandos | 30 segundos |
| **[📖 LEIA_ME_PRIMEIRO.md](./LEIA_ME_PRIMEIRO.md)** | Primeira vez no projeto | 5 minutos |
| **[🎯 COMO_EXECUTAR.md](./COMO_EXECUTAR.md)** | Guia detalhado de execução | 10 minutos |
| **[📦 INSTALACAO.md](./INSTALACAO.md)** | Instalação completa | 15 minutos |

---

## 📖 Documentação Técnica

| Arquivo | Conteúdo |
|---------|----------|
| **[README.md](./README.md)** | Visão geral do projeto completo |
| **[QUICKSTART.md](./QUICKSTART.md)** | Guia de início rápido original |
| **[PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md)** | Estrutura de arquivos e pastas |
| **[API.md](./API.md)** | Documentação da API REST |
| **[WEBCAM_INFERENCE_SETUP.md](./WEBCAM_INFERENCE_SETUP.md)** | Setup de webcam e inferência |
| **[CAMERA_TROUBLESHOOTING.md](./CAMERA_TROUBLESHOOTING.md)** | 🔧 Solução de problemas de câmera |

---

## 🔐 Autenticação

| Arquivo | Conteúdo |
|---------|----------|
| **[AUTH_FIX_COMPLETE.md](./AUTH_FIX_COMPLETE.md)** | Correções de autenticação |
| **[AUTH_TROUBLESHOOTING.md](./AUTH_TROUBLESHOOTING.md)** | Solução de problemas de auth |
| **[DEMO_MODE_SETUP.md](./DEMO_MODE_SETUP.md)** | Configuração do modo demo |

---

## 🏗️ Arquitetura

| Arquivo | Conteúdo |
|---------|----------|
| **[diagrams/INDEX.md](./diagrams/INDEX.md)** | Índice de todos os diagramas |
| **[diagrams/EXECUTIVE_SUMMARY.md](./diagrams/EXECUTIVE_SUMMARY.md)** | Resumo executivo da arquitetura |
| **[diagrams/QUICK_REFERENCE.md](./diagrams/QUICK_REFERENCE.md)** | Referência rápida de diagramas |

---

## 🤖 Modelos de IA

| Arquivo | Conteúdo |
|---------|----------|
| **[models/README.md](./models/README.md)** | Como treinar modelos YOLO customizados |

---

## 🗄️ Banco de Dados

| Arquivo | Conteúdo |
|---------|----------|
| **[supabase/migrations/README.md](./supabase/migrations/README.md)** | Migrations e schema do banco |
| **[supabase/migrations/001_create_ecovision_tables.sql](./supabase/migrations/001_create_ecovision_tables.sql)** | Schema completo das tabelas |

---

## 📝 Outros

| Arquivo | Conteúdo |
|---------|----------|
| **[CHANGELOG.md](./CHANGELOG.md)** | Histórico de mudanças |
| **[Attributions.md](./Attributions.md)** | Créditos e atribuições |
| **[guidelines/Guidelines.md](./guidelines/Guidelines.md)** | Diretrizes de desenvolvimento |

---

## 🎯 Fluxo Recomendado de Leitura

### 1️⃣ Iniciante (Quer apenas rodar)
```
START.md → Executar comandos → Testar no navegador
```

### 2️⃣ Desenvolvedor (Primeira vez)
```
LEIA_ME_PRIMEIRO.md → COMO_EXECUTAR.md → Testar → README.md
```

### 3️⃣ Desenvolvedor (Quer entender tudo)
```
README.md → PROJECT_STRUCTURE.md → diagrams/INDEX.md → API.md
```

### 4️⃣ Desenvolvedor (Problemas)
```
COMO_EXECUTAR.md (Troubleshooting) → AUTH_TROUBLESHOOTING.md → GitHub Issues
```

### 5️⃣ Arquiteto (Quer visualizar)
```
diagrams/EXECUTIVE_SUMMARY.md → diagrams/INDEX.md → Ver todos os diagramas
```

### 6️⃣ Cientista de Dados (Treinar modelos)
```
models/README.md → Preparar dataset → Treinar YOLO customizado
```

---

## 📊 Hierarquia de Documentação

```
📦 EcoVision Documentation
│
├── 🚀 Quick Start
│   ├── START.md                      ← Comandos rápidos
│   ├── LEIA_ME_PRIMEIRO.md          ← Overview
│   ├── COMO_EXECUTAR.md             ← Guia detalhado
│   └── INSTALACAO.md                ← Instalação completa
│
├── 📖 Core Documentation
│   ├── README.md                     ← Documentação principal
│   ├── QUICKSTART.md                 ← Guia original
│   └── PROJECT_STRUCTURE.md          ← Estrutura do projeto
│
├── 🔧 Technical Guides
│   ├── API.md                        ← API REST
│   ├── WEBCAM_INFERENCE_SETUP.md     ← Webcam + IA
│   └── models/README.md              ← Treinamento YOLO
│
├── 🔐 Authentication
│   ├── AUTH_FIX_COMPLETE.md
│   ├── AUTH_TROUBLESHOOTING.md
│   └── DEMO_MODE_SETUP.md
│
├── 🏗️ Architecture
│   ├── diagrams/INDEX.md
│   ├── diagrams/EXECUTIVE_SUMMARY.md
│   └── diagrams/*.puml
│
└── 📝 Other
    ├── CHANGELOG.md
    ├── Attributions.md
    └── guidelines/Guidelines.md
```

---

## 🎯 Por Tipo de Usuário

### 👨‍💻 Desenvolvedor Frontend
```
1. COMO_EXECUTAR.md
2. PROJECT_STRUCTURE.md (seção /components)
3. API.md (endpoints do backend)
```

### 🐍 Desenvolvedor Python/ML
```
1. WEBCAM_INFERENCE_SETUP.md
2. models/README.md
3. inference_server.py (código fonte)
```

### 🗄️ Desenvolvedor Backend
```
1. API.md
2. supabase/migrations/001_create_ecovision_tables.sql
3. supabase/functions/server/index.tsx
```

### 🏗️ Arquiteto de Software
```
1. diagrams/EXECUTIVE_SUMMARY.md
2. diagrams/INDEX.md
3. PROJECT_STRUCTURE.md
```

### 👔 Gerente de Projeto
```
1. LEIA_ME_PRIMEIRO.md
2. README.md
3. diagrams/EXECUTIVE_SUMMARY.md
```

---

## 🔍 Buscar por Tópico

### Instalação
- START.md
- COMO_EXECUTAR.md
- INSTALACAO.md
- QUICKSTART.md

### Webcam
- COMO_EXECUTAR.md (seção "O Que Vai Acontecer")
- WEBCAM_INFERENCE_SETUP.md
- components/CameraFeed.tsx (código fonte)

### YOLO/IA
- models/README.md
- WEBCAM_INFERENCE_SETUP.md
- inference_server.py (código fonte)

### Autenticação
- AUTH_FIX_COMPLETE.md
- AUTH_TROUBLESHOOTING.md
- DEMO_MODE_SETUP.md

### Banco de Dados
- supabase/migrations/001_create_ecovision_tables.sql
- API.md (endpoints de banco)
- diagrams/database-diagram.puml

### API
- API.md
- supabase/functions/server/index.tsx

### Arquitetura
- diagrams/INDEX.md
- diagrams/EXECUTIVE_SUMMARY.md
- PROJECT_STRUCTURE.md

### Troubleshooting
- COMO_EXECUTAR.md (seção "Troubleshooting")
- AUTH_TROUBLESHOOTING.md
- WEBCAM_INFERENCE_SETUP.md (seção "Problemas Comuns")

---

<div align="center">

**📚 EcoVision Documentation Index**

**Documentação completa e organizada para máxima produtividade**

</div>
