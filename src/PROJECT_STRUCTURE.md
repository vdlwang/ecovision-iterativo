# 📁 EcoVision - Estrutura do Projeto

Documentação completa da organização de arquivos e responsabilidades de cada componente.

## 🌳 Árvore de Diretórios

```
ecovision/
│
├── 📱 FRONTEND (React + TypeScript)
│   ├── App.tsx                          # Componente principal, roteamento
│   ├── components/                      # Componentes React
│   │   ├── Login.tsx                    # Tela de login com Google
│   │   ├── Sidebar.tsx                  # Menu lateral (Monitor, Cancelas, etc)
│   │   ├── MonitorPanel.tsx             # Tela principal de monitoramento
│   │   ├── CameraFeed.tsx               # ⭐ Captura webcam + inferência
│   │   ├── GateConfiguration.tsx        # Configuração de cancelas
│   │   ├── AccuracyControl.tsx          # Controle de modelo e confiança
│   │   ├── StatisticsPanel.tsx          # Dashboard com gráficos
│   │   ├── UserProfile.tsx              # Perfil do usuário
│   │   ├── ConveyorSystem.tsx           # Animação da esteira
│   │   └── ui/                          # Componentes ShadCN
│   │       ├── button.tsx
│   │       ├── card.tsx
│   │       ├── badge.tsx
│   │       └── ...
│   ├── utils/
│   │   └── supabase/
│   │       ├── client.tsx               # Cliente Supabase
│   │       └── info.tsx                 # Project ID e chaves
│   └── styles/
│       └── globals.css                  # Estilos globais + paleta de cores
│
├── 🐍 SERVIDOR DE INFERÊNCIA (Python + FastAPI)
│   ├── inference_server.py              # ⭐ API de inferência YOLO
│   ├── requirements.txt                 # Dependências Python
│   ├── test_setup.py                    # Script de verificação
│   ├── run_dev.sh                       # Script de inicialização (Linux/Mac)
│   ├── run_dev.bat                      # Script de inicialização (Windows)
│   └── models/                          # Modelos YOLO (.pt)
│       ├── yolov8n.pt                   # Modelo Nano (download automático)
│       ├── yolov8s.pt                   # Modelo Small (download automático)
│       ├── yolov8m.pt                   # Modelo Medium (download automático)
│       └── README.md                    # Guia de treinamento
│
├── ⚡ BACKEND (Supabase Edge Functions - Deno + Hono)
│   └── supabase/
│       ├── functions/
│       │   └── server/
│       │       ├── index.tsx            # ⭐ API principal (endpoints)
│       │       ├── models.tsx           # Classes UML (legacy)
│       │       └── kv_store.tsx         # 🔒 PROTEGIDO (não modificar)
│       └── migrations/
│           ├── 001_create_ecovision_tables.sql  # ⭐ Schema do banco
│           └── README.md
│
├── 🗄️ BANCO DE DADOS (PostgreSQL via Supabase)
│   # Tabelas criadas pela migração:
│   ├── profiles                         # Perfis de usuários
│   ├── user_sessions                    # Sessões de uso
│   ├── inferences                       # ⭐ Detecções de IA
│   ├── system_config                    # Configurações do sistema
│   ├── statistics                       # Estatísticas agregadas
│   └── system_logs                      # Logs do sistema
│
├── 📊 DOCUMENTAÇÃO
│   ├── README.md                        # Visão geral do projeto
│   ├── QUICKSTART.md                    # ⭐ Guia de início rápido
│   ├── WEBCAM_INFERENCE_SETUP.md        # ⭐ Guia completo de setup
│   ├── API.md                           # Documentação da API
│   ├── SETUP.md                         # Setup inicial
│   ├── CHANGELOG.md                     # Histórico de mudanças
│   └── PROJECT_STRUCTURE.md             # Este arquivo
│
└── 📐 DIAGRAMAS UML
    └── diagrams/
        ├── architecture-diagram.puml    # Arquitetura do sistema
        ├── class-diagram.puml           # Diagrama de classes
        ├── component-diagram.puml       # Componentes
        ├── sequence-diagram.puml        # Fluxo de sequência
        ├── data-flow-diagram.puml       # Fluxo de dados
        ├── database-diagram.puml        # Modelo do banco
        └── INDEX.md                     # Índice dos diagramas
```

---

## 🔄 Fluxo de Dados Completo

### 1️⃣ Captura de Frame (Frontend)

```typescript
// components/CameraFeed.tsx - linha 126-204

// A cada 2 segundos:
1. Captura frame da webcam via getUserMedia()
2. Desenha frame em canvas
3. Converte para base64
4. Remove prefixo "data:image/jpeg;base64,"
5. Prepara payload JSON
```

### 2️⃣ Envio para Backend (Frontend → Backend)

```typescript
// components/CameraFeed.tsx - linha 147-161

POST https://{projectId}.supabase.co/functions/v1/make-server-ea835390/inference
Headers:
  Authorization: Bearer {userToken}
  Content-Type: application/json
Body:
  {
    "image_base64": "...",
    "model_version": "YOLOv8n",
    "min_confidence": 85
  }
```

### 3️⃣ Proxy para Servidor Python (Backend → Python)

```typescript
// supabase/functions/server/index.tsx - linha 125-170

1. Autentica usuário via token JWT
2. Obtém configuração ativa do banco
3. Faz requisição para servidor Python:
   POST http://localhost:8000/inference
4. Aguarda resposta do YOLO
```

### 4️⃣ Inferência YOLO (Servidor Python)

```python
# inference_server.py - linha 239-309

1. Decodifica base64 → imagem numpy
2. Carrega modelo YOLO (cache)
3. Executa predição com Ultralytics
4. Processa detecções:
   - Filtra por confiança mínima
   - Mapeia classes → materiais
   - Extrai bounding boxes
5. Retorna JSON com detecções
```

### 5️⃣ Salvar no Banco (Backend)

```typescript
// supabase/functions/server/index.tsx - linha 146-164

Para cada detecção:
1. Determina qual cancela acionar
2. Verifica se confiança >= mínima
3. Insere em tabela 'inferences':
   INSERT INTO inferences (
     user_id,
     session_id,
     material_detected,
     confidence,
     gate_number,
     gate_activated,
     model_version,
     processing_time_ms,
     bounding_box
   )
```

### 6️⃣ Renderizar no Frontend

```typescript
// components/CameraFeed.tsx - linha 206-259

1. Recebe detecções do backend
2. Atualiza state do React
3. Desenha bounding boxes no canvas overlay
4. Chama callback onDetection (notifica MonitorPanel)
5. MonitorPanel adiciona em "Detecções Recentes"
```

### 7️⃣ Atualizar Dashboard

```typescript
// components/StatisticsPanel.tsx - linha 50-80

A cada 30 segundos (ou ao clicar "Atualizar"):
1. Faz GET /stats
2. Backend consulta banco:
   SELECT material_detected, COUNT(*)
   FROM inferences
   WHERE user_id = $1
   GROUP BY material_detected
3. Renderiza gráficos com Recharts
```

---

## 🎯 Componentes Principais

### 📱 Frontend

#### App.tsx
**Responsabilidade:** Roteamento e estado global
```typescript
- Gerencia autenticação (Supabase Auth)
- Estado: isSystemRunning, minAccuracy, modelVersion, gateConfigs
- Handlers: handleToggleSystem, handleAccuracyChange, etc
- Renderiza Sidebar + conteúdo ativo (Monitor, Cancelas, etc)
```

#### CameraFeed.tsx ⭐
**Responsabilidade:** Captura webcam + inferência
```typescript
- Enumera dispositivos de vídeo
- Inicia/para stream com getUserMedia()
- Captura frames a cada 2s
- Envia para backend para inferência
- Desenha bounding boxes
- Gerencia estado: devices, stream, detections
```

**Props importantes:**
```typescript
interface CameraFeedProps {
  isRunning: boolean;          // Sistema ligado/desligado
  onDetection?: (detection) => void;  // Callback
  modelVersion: string;        // YOLOv8n, YOLOv8s, YOLOv8m
  minConfidence: number;       // 0-100
  userToken?: string;          // Token JWT para auth
}
```

#### MonitorPanel.tsx
**Responsabilidade:** Tela principal de monitoramento
```typescript
- Renderiza CameraFeed
- Mostra animação da esteira
- Lista detecções recentes
- Indica estado das cancelas
- Gerencia histórico de detecções
```

#### StatisticsPanel.tsx ⭐
**Responsabilidade:** Dashboard com dados reais
```typescript
- Carrega estatísticas do banco via GET /stats
- Renderiza gráficos:
  - PieChart: Distribuição por material
  - BarChart: Acionamentos por cancela
- Mostra métricas: total, confiança média, sessões
- Lista detecções recentes do banco
- Auto-atualiza a cada 30s se sistema rodando
```

### 🐍 Servidor Python

#### inference_server.py ⭐
**Responsabilidade:** API de inferência com YOLO
```python
Endpoints:
  GET  /health              # Health check
  GET  /models              # Lista modelos disponíveis
  POST /models/load         # Carrega modelo específico
  POST /inference           # Inferência com base64
  POST /inference/file      # Inferência com arquivo

Funções principais:
  load_model()              # Carrega YOLO (cache)
  base64_to_image()         # Decodifica base64
  map_class_to_material()   # COCO → material
  process_detections()      # Processa resultados YOLO
```

**Mapeamento de Classes:**
```python
CLASS_TO_MATERIAL = {
    # Papel
    "book": "papel",
    "newspaper": "papel",
    "cardboard": "papel",
    
    # Metal
    "can": "metal",
    "fork": "metal",
    
    # Plástico
    "bottle": "plastico",
    "cup": "plastico",
    
    # Vidro
    "wine glass": "vidro",
    "glass": "vidro"
}
```

### ⚡ Backend Supabase

#### index.tsx ⭐
**Responsabilidade:** API intermediária (proxy + persistência)
```typescript
Endpoints:
  POST /config              # Salva configuração
  GET  /config              # Obtém configuração ativa
  POST /inference           # Proxy para servidor Python + salva BD
  GET  /stats               # Estatísticas do usuário
  GET  /stats/period        # Estatísticas por período
  POST /session/end         # Encerra sessão
  POST /logs                # Salva log
  GET  /logs                # Obtém logs

Funções auxiliares:
  getUserFromToken()        # Extrai user_id do JWT
  getOrCreateSession()      # Gerencia sessões
```

---

## 🗄️ Schema do Banco de Dados

### Tabela: inferences ⭐
**Armazena todas as detecções da IA**

```sql
CREATE TABLE inferences (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users NOT NULL,
  session_id UUID REFERENCES user_sessions,
  material_detected TEXT NOT NULL,        -- papel, metal, plastico, vidro
  confidence DECIMAL(5,2) NOT NULL,       -- 0.00 - 100.00
  gate_number INTEGER NOT NULL,           -- 1, 2, 3
  gate_activated BOOLEAN DEFAULT false,   -- Cancela foi acionada?
  model_version TEXT DEFAULT 'YOLOv8n',   -- Modelo usado
  processing_time_ms INTEGER,             -- Tempo de inferência
  bounding_box JSONB,                     -- {x, y, width, height}
  timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_inferences_user ON inferences(user_id);
CREATE INDEX idx_inferences_material ON inferences(material_detected);
CREATE INDEX idx_inferences_timestamp ON inferences(timestamp);
```

**Exemplo de registro:**
```json
{
  "id": "a1b2c3d4-...",
  "user_id": "user123",
  "session_id": "session456",
  "material_detected": "plastico",
  "confidence": 92.30,
  "gate_number": 2,
  "gate_activated": true,
  "model_version": "YOLOv8n",
  "processing_time_ms": 145,
  "bounding_box": {
    "x": 120.5,
    "y": 80.3,
    "width": 150.2,
    "height": 300.8
  },
  "timestamp": "2025-11-09T12:34:56.789Z"
}
```

### Tabela: user_sessions
**Rastreia sessões de uso**

```sql
CREATE TABLE user_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users NOT NULL,
  session_token TEXT UNIQUE NOT NULL,
  started_at TIMESTAMPTZ DEFAULT NOW(),
  ended_at TIMESTAMPTZ,
  inferences_count INTEGER DEFAULT 0,
  user_agent TEXT,
  device_info JSONB
);
```

### Tabela: system_config
**Configurações do sistema por usuário**

```sql
CREATE TABLE system_config (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users NOT NULL,
  gate_1_material TEXT,                  -- papel, metal, plastico, vidro
  gate_2_material TEXT,
  gate_3_material TEXT,
  min_confidence INTEGER DEFAULT 85,
  model_version TEXT DEFAULT 'YOLOv8n',
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Tabela: statistics
**Estatísticas agregadas diárias**

```sql
CREATE TABLE statistics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users NOT NULL,
  date DATE NOT NULL,
  total_inferences INTEGER DEFAULT 0,
  papel_count INTEGER DEFAULT 0,
  metal_count INTEGER DEFAULT 0,
  plastico_count INTEGER DEFAULT 0,
  vidro_count INTEGER DEFAULT 0,
  avg_confidence DECIMAL(5,2),
  avg_processing_time_ms INTEGER
);
```

---

## 🔐 Autenticação e Segurança

### Fluxo de Autenticação

```
1. Usuário clica "Entrar com Google"
   ↓
2. Supabase Auth redireciona para Google OAuth
   ↓
3. Usuário autoriza aplicação
   ↓
4. Supabase cria sessão e retorna access_token (JWT)
   ↓
5. Frontend armazena token no state
   ↓
6. Todas requisições incluem: Authorization: Bearer {token}
   ↓
7. Backend valida token e extrai user_id
   ↓
8. Queries ao banco filtram por user_id
```

### Row Level Security (RLS)

```sql
-- Exemplo: Usuário só vê suas próprias inferências
CREATE POLICY "Users can view own inferences"
  ON inferences FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own inferences"
  ON inferences FOR INSERT
  WITH CHECK (auth.uid() = user_id);
```

---

## 🎨 Paleta de Cores

Definida em `styles/globals.css`:

```css
:root {
  /* Verde Primário (Reciclagem) */
  --recycling-primary: #034732;
  --recycling-primary-dark: #023428;
  --recycling-primary-darker: #011f19;
  --recycling-lighter: #d4e8e1;
  --recycling-accent: #008148;
  
  /* Materiais */
  --material-paper: #163b6f;      /* Azul */
  --material-metal: #196626;      /* Verde Escuro */
  --material-plastic: #dc1f2e;    /* Vermelho Vibrante */
  --material-glass: #d2b91f;      /* Amarelo/Dourado */
  --material-rejected: #ff4444;   /* Vermelho (rejeitado) */
}
```

---

## 📝 Convenções de Código

### TypeScript/React
- **Componentes:** PascalCase (`CameraFeed.tsx`)
- **Hooks:** camelCase (`useState`, `useEffect`)
- **Props:** Interfaces com sufixo `Props` (`CameraFeedProps`)
- **Handlers:** Prefixo `handle` (`handleCameraDetection`)

### Python
- **Funções:** snake_case (`load_model`, `base64_to_image`)
- **Classes:** PascalCase (`InferenceResponse`)
- **Constantes:** UPPER_SNAKE_CASE (`CLASS_TO_MATERIAL`)

### SQL
- **Tabelas:** snake_case plural (`inferences`, `user_sessions`)
- **Colunas:** snake_case (`material_detected`, `gate_number`)
- **Índices:** Prefixo `idx_` (`idx_inferences_user`)

---

## 🔧 Variáveis de Ambiente

### Frontend (.env)
```bash
VITE_SUPABASE_URL=https://xxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGc...
```

### Backend (Supabase Secrets)
```bash
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGc...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...
INFERENCE_SERVER_URL=http://localhost:8000  # ou URL de produção
```

---

## 📊 Performance

### Métricas Esperadas

| Componente | Métrica | Valor Esperado |
|------------|---------|----------------|
| Webcam Capture | FPS | 30 |
| Inferência (YOLOv8n CPU) | Latência | 100-500ms |
| Inferência (YOLOv8n GPU) | Latência | 10-50ms |
| Backend API | Latência | <100ms |
| Frontend Render | FPS | 60 |
| Intervalo de Captura | Tempo | 2s |

### Otimizações Possíveis

1. **Reduzir resolução da webcam** (1920x1080 → 640x480)
2. **Aumentar intervalo de captura** (2s → 5s)
3. **Usar modelo mais leve** (YOLOv8s → YOLOv8n)
4. **Implementar GPU** (CUDA) para inferência
5. **Cache de frames** para reduzir re-processamento

---

## 📚 Recursos Adicionais

- **Ultralytics Docs:** https://docs.ultralytics.com
- **Supabase Docs:** https://supabase.com/docs
- **FastAPI Docs:** https://fastapi.tiangolo.com
- **React Docs:** https://react.dev

---

**Última atualização:** 09 de Novembro de 2025
