# 📚 Guia do Projeto EcoVision

## 🎯 Início Rápido

1. **[README.md](./README.md)** - Documentação principal do projeto
2. **[diagrams/INDEX.md](./diagrams/INDEX.md)** - Diagramas de arquitetura
3. **[models/README.md](./models/README.md)** - Guia dos modelos YOLO

## 📁 Estrutura do Código

### Frontend (React + TypeScript)

```
components/
├── AccuracyControl.tsx       # Controle de confiança mínima
├── CameraFeed.tsx           # Feed de webcam + detecções
├── ConveyorSystem.tsx       # Animação da esteira
├── GateConfiguration.tsx    # Config das cancelas
├── Login.tsx                # Autenticação
├── MonitorPanel.tsx         # Painel de monitoramento
├── Sidebar.tsx              # Menu lateral
├── StatisticsPanel.tsx      # Dashboard com gráficos
└── UserProfile.tsx          # Perfil do usuário
```

### Backend (Supabase Edge Functions)

```
supabase/functions/server/
├── index.tsx                # API principal (Hono)
├── kv_store.tsx            # Utilitário KV Store
│
├── Camera.tsx              # Classe Camera
├── Usuario.tsx             # Classe Usuario
├── OutputData.tsx          # Classe OutputData
├── Atuador.tsx             # Interface IAtuador + ControladorSerial
├── Esteira.tsx             # Classe Esteira
├── Cancela.tsx             # Classe Cancela
├── RegistroProcessamento.tsx
├── BancoDeDados.tsx        # Classe BancoDeDados
├── ModeloIA.tsx            # Classe ModeloIA
├── Dashboard.tsx           # Classe Dashboard
└── Autenticacao.tsx        # Classe Autenticacao
```

**Nota:** As classes do backend estão separadas em arquivos individuais para melhor organização e manutenibilidade. Atualmente, não são utilizadas diretamente no código, mas estão disponíveis para futuras implementações.

### Python (Servidor de Inferência)

```
inference_server.py         # FastAPI + YOLO
requirements.txt            # Dependências Python
test_setup.py              # Script de teste
```

## 🏗️ Arquitetura

### Fluxo Principal

1. **Câmera** → Frontend captura frames via `getUserMedia`
2. **Frontend** → Converte para base64 e envia para backend
3. **Backend** → Autentica e encaminha para Python
4. **Python** → Processa com YOLO e retorna detecções
5. **Backend** → Salva no PostgreSQL
6. **Frontend** → Renderiza bounding boxes e atualiza UI

### Componentes

- **Frontend:** React + TypeScript + Tailwind + Shadcn/UI
- **Backend:** Supabase Edge Functions (Deno + Hono)
- **Banco:** PostgreSQL com RLS
- **IA:** Python + FastAPI + Ultralytics YOLO
- **Auth:** Supabase Auth (Google OAuth)

## 📊 Diagramas

Consulte `/diagrams/INDEX.md` para diagramas completos:

- **Arquitetura** - Visão geral do sistema
- **Classes** - Modelo de domínio
- **Componentes** - Estrutura React
- **Fluxo de Dados** - Comunicação entre camadas
- **Banco de Dados** - Schema e relacionamentos
- **Sequência** - Fluxo de detecção

## 🚀 Executar o Projeto

```bash
# Instalar dependências Python
pip install -r requirements.txt

# Executar servidor Python
python inference_server.py

# Em outro terminal, executar frontend
# (o Figma Make já gerencia isso)
```

## 🔧 Configuração

### Variáveis de Ambiente (Backend)

```bash
SUPABASE_URL=https://...
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
INFERENCE_SERVER_URL=http://localhost:8000
```

### Banco de Dados

Execute a migração em `/supabase/migrations/001_create_ecovision_tables.sql` no Supabase Dashboard.

## 📝 Paleta de Cores

Definida em `/styles/globals.css`:

- **Verde EcoVision:** `#034732` a `#abf2ab`
- **Papel (Azul):** `#163b6f`
- **Metal (Verde):** `#196626`
- **Plástico (Vermelho vibrante):** `#dc1f2e`
- **Vidro (Amarelo):** `#d2b91f`

## 🤝 Contribuindo

1. Entenda a arquitetura consultando os diagramas
2. Siga a estrutura de pastas existente
3. Adicione componentes em `/components`
4. Classes do backend em `/supabase/functions/server`
5. Use Tailwind + Shadcn/UI para UI
6. Mantenha a paleta de cores consistente

---

**EcoVision** - Sistema de Reciclagem Inteligente 🌱♻️
