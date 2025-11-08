# 📊 Índice de Diagramas do EcoVision

Documentação visual completa do sistema EcoVision através de diagramas UML.

---

## 🗂️ Navegação Rápida

| Diagrama | Arquivo | Propósito | Quando Usar |
|----------|---------|-----------|-------------|
| 🏗️ **Arquitetura** | [`architecture-diagram.puml`](./architecture-diagram.puml) | Visão geral da arquitetura de três camadas | Para entender a estrutura macro do sistema |
| 📦 **Classes** | [`class-diagram.puml`](./class-diagram.puml) | Estrutura de classes e relacionamentos | Para desenvolver ou modificar classes |
| 🔄 **Sequência** | [`sequence-diagram.puml`](./sequence-diagram.puml) | Fluxos de interação entre componentes | Para entender comportamentos e chamadas |
| 📊 **Fluxo de Dados** | [`data-flow-diagram.puml`](./data-flow-diagram.puml) | Fluxo de dados em tempo real | Para otimizar performance e debug |
| 🧩 **Componentes React** | [`component-diagram.puml`](./component-diagram.puml) | Estrutura de componentes e props | Para trabalhar no frontend |
| 🗄️ **Banco de Dados** | [`database-diagram.puml`](./database-diagram.puml) | Modelo de dados PostgreSQL completo | Para trabalhar com persistência e queries |

---

## 📋 Detalhamento por Diagrama

### 🏗️ 1. Arquitetura de Três Camadas
**Arquivo:** `architecture-diagram.puml`

**Mostra:**
- ✅ Camada 1: Frontend (React + Tailwind)
- ✅ Camada 2: Server (Hono + Edge Functions)
- ✅ Camada 3: Database (Supabase + PostgreSQL)
- ✅ Hardware externo (ESP32, Webcam, Atuadores)
- ✅ Fluxo HTTP REST entre camadas
- ✅ Endpoints principais da API

**Use para:**
- Onboarding de novos desenvolvedores
- Apresentações do projeto
- Planejamento de deploys
- Documentação de infraestrutura

---

### 📦 2. Diagrama de Classes
**Arquivo:** `class-diagram.puml`

**Mostra:**
- ✅ Componentes React (App, Login, MonitorPanel, etc.)
- ✅ Classes de domínio (Camera, Esteira, Cancela, ModeloIA, etc.)
- ✅ Interfaces (IAtuador)
- ✅ Classes de dados (OutputData, RegistroProcessamento, Usuario)
- ✅ Infraestrutura (BancoDeDados, SupabaseClient, KeyValueStore)
- ✅ Relacionamentos: herança, composição, uso, dependência

**Use para:**
- Desenvolver novas features
- Refatoração de código
- Identificar responsabilidades
- Planejar testes unitários

---

### 🔄 3. Diagramas de Sequência
**Arquivo:** `sequence-diagram.puml`

**Contém 5 fluxos principais:**

#### 3.1. Fluxo de Autenticação
- Login com Google OAuth
- Modo Demo
- Verificação de sessão

#### 3.2. Fluxo de Configuração
- Configuração de cancelas
- Ajuste de confiança mínima
- Seleção de modelo YOLO

#### 3.3. Fluxo de Monitoramento e Detecção 🔥
- Início do sistema (esteira + modelo)
- Loop de detecção (3s)
- Inferência YOLO
- Decisão de acionamento
- Controle de cancelas via serial
- Registro no banco

#### 3.4. Fluxo de Estatísticas
- Carregamento de dados
- Agregação de métricas
- Atualização de gráficos

#### 3.5. Fluxo de Logout
- Encerramento de sessão
- Limpeza de estado

**Use para:**
- Debugar comportamentos
- Entender timing de operações
- Identificar gargalos
- Documentar APIs

---

### 📊 4. Fluxo de Dados em Tempo Real
**Arquivo:** `data-flow-diagram.puml`

**Mostra:**
- ✅ Captura de vídeo da webcam (30fps)
- ✅ Loop de detecção (a cada 3 segundos)
- ✅ Inferência YOLO e bounding boxes
- ✅ Lógica de decisão (confiança + matching)
- ✅ Comandos seriais para ESP32
- ✅ Acionamento de cancelas (abre → 2s → fecha)
- ✅ Persistência no banco de dados
- ✅ Feedback visual (canvas + toast)
- ✅ Dashboard paralelo com polling (10s)

**Métricas incluídas:**
- FPS da câmera: 30fps
- Frequência de detecção: 1x/3s
- Tempo de acionamento: 2s
- Atualização dashboard: 10s

**Use para:**
- Otimizar performance
- Ajustar timings
- Identificar race conditions
- Validar fluxo de dados

---

### 🧩 5. Componentes React
**Arquivo:** `component-diagram.puml`

**Mostra:**
- ✅ Hierarquia de componentes React
- ✅ Props e tipos de cada componente
- ✅ Estado local (useState)
- ✅ Refs (useRef)
- ✅ Uso de componentes Shadcn/UI
- ✅ Integração com Supabase
- ✅ Chamadas à API REST

**Componentes documentados:**
- `App.tsx` (root)
- `Login.tsx`
- `Sidebar.tsx`
- `MonitorPanel.tsx` + `CameraFeed.tsx` + `ConveyorSystem.tsx`
- `GateConfiguration.tsx`
- `AccuracyControl.tsx`
- `StatisticsPanel.tsx`
- `UserProfile.tsx`

**Use para:**
- Desenvolver novos componentes
- Entender prop drilling
- Refatorar componentes
- Planejar testes de UI

---

### 🗄️ 6. Diagrama de Banco de Dados
**Arquivo:** `database-diagram.puml`

**Mostra:**
- ✅ Tabelas customizadas (profiles, user_sessions, inferences, system_config, statistics, system_logs)
- ✅ Integração com Supabase Auth (auth.users)
- ✅ Relacionamentos e foreign keys
- ✅ Constraints e validações (CHECK, UNIQUE)
- ✅ Índices para performance
- ✅ Triggers e functions do PostgreSQL
- ✅ Views e materialized views
- ✅ Row Level Security (RLS) policies

**Tabelas principais:**
- `profiles` - Dados adicionais do usuário
- `user_sessions` - Rastreamento de sessões
- `inferences` - Registro de cada detecção IA
- `system_config` - Configurações por usuário
- `statistics` - Agregação diária de dados
- `system_logs` - Logs e auditoria

**Use para:**
- Criar novas tabelas e migrações
- Escrever queries otimizadas
- Entender relacionamentos de dados
- Planejar índices e constraints
- Configurar Row Level Security

---

## 🎨 Convenções de Cores

Todos os diagramas seguem a paleta de cores do EcoVision:

| Cor | Hex | Uso |
|-----|-----|-----|
| 🟢 Verde Escuro | `#034732` | Componente principal, esteira |
| 🟢 Verde Claro | `#ABF2AB` | Componentes React, UI |
| 🟢 Verde Médio | `#008148` | Utilitários, helpers |
| 🔵 Azul Papel | `#163B6F` | Papel/Papelão, persistência |
| 🟢 Verde Metal | `#196626` | Metal, lógica de negócio |
| 🔴 Vermelho Plástico | `#DC1F2E` | Plástico, perfil |
| 🟡 Amarelo Vidro | `#D2B91F` | Vidro, dashboard |
| 🟠 Laranja | `#FEF4ED` | Backend, servidor |
| 🔵 Azul Claro | `#E8F4FD` | Database, autenticação |
| 🟡 Amarelo Claro | `#FFF9E8` | Hardware, externo |
| 🟢 Verde Monitor | `#EDFEF4` | Aba Monitor |

---

## 📚 Como Usar Este Índice

### Para Novos Desenvolvedores
1. Comece com **Arquitetura** para visão geral
2. Veja **Componentes React** para entender o frontend
3. Consulte **Classes** para entender o backend
4. Use **Sequência** para debugar fluxos

### Para Features Novas
1. **Componentes React**: Identifique onde adicionar o componente
2. **Classes**: Crie classes de domínio necessárias
3. **Sequência**: Documente o novo fluxo
4. **Fluxo de Dados**: Atualize se houver novo fluxo de dados

### Para Debugging
1. **Sequência**: Identifique o fluxo com problema
2. **Fluxo de Dados**: Verifique timings e dados
3. **Classes**: Verifique responsabilidades
4. **Componentes React**: Verifique props e estado

### Para Otimização
1. **Fluxo de Dados**: Identifique gargalos
2. **Sequência**: Otimize chamadas desnecessárias
3. **Arquitetura**: Considere mudanças estruturais

---

## 🔧 Manutenção dos Diagramas

### Quando Atualizar

| Mudança no Código | Diagrama(s) a Atualizar |
|-------------------|-------------------------|
| Nova classe/componente | Classes + Componentes React |
| Novo endpoint API | Arquitetura + Sequência |
| Mudança em props | Componentes React |
| Novo fluxo de usuário | Sequência |
| Mudança em timing/performance | Fluxo de Dados |
| Nova tabela/storage | Arquitetura + Classes |

### Checklist de Atualização
- [ ] Código alterado
- [ ] Diagrama(s) identificado(s)
- [ ] Arquivo .puml editado
- [ ] Diagrama testado (renderizado)
- [ ] Cores e formatação mantidas
- [ ] Notas e legendas atualizadas
- [ ] INDEX.md atualizado se necessário

---

## 🚀 Quick Start

```bash
# Clone o repositório
git clone <repo-url>
cd ecovision

# Visualize no VS Code (recomendado)
code diagrams/

# Instale extensão PlantUML
# Pressione Alt+D para preview

# Ou gere imagens PNG
cd diagrams
plantuml *.puml

# Ou gere SVG (melhor qualidade)
plantuml -tsvg *.puml
```

---

## 📖 Recursos Adicionais

- [README.md](./README.md) - Instruções detalhadas
- [PlantUML Docs](https://plantuml.com/)
- [EcoVision API.md](../API.md) - Documentação da API
- [EcoVision SETUP.md](../SETUP.md) - Configuração do projeto
- [Guidelines.md](../guidelines/Guidelines.md) - Diretrizes de desenvolvimento

---

## 💡 Dicas

- **VS Code**: Use `Ctrl+Shift+P` → "PlantUML: Export Current Diagram"
- **Online**: Use [plantuml.com/plantuml](http://www.plantuml.com/plantuml) para preview rápido
- **SVG**: Melhor para documentação (escalável, texto selecionável)
- **PNG**: Melhor para apresentações (compatibilidade universal)

---

*Última atualização: 08/11/2025*
