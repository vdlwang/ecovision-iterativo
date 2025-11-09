# 📚 Índice de Documentação - EcoVision

## 🚀 Início Rápido

Novo no projeto? Comece aqui:

1. **[STATUS.md](/STATUS.md)** - Status atual do sistema e visão geral
2. **[README.md](/README.md)** - Visão geral do projeto
3. **[QUICKSTART_ONNX.md](/QUICKSTART_ONNX.md)** - Guia rápido para começar

---

## 🎯 Por Caso de Uso

### "Quero entender o sistema"
- **[README.md](/README.md)** - O que é o EcoVision
- **[PROJECT_GUIDE.md](/PROJECT_GUIDE.md)** - Guia completo do projeto
- **[STRUCTURE.md](/STRUCTURE.md)** - Estrutura de arquivos
- **[diagrams/](/diagrams/)** - Diagramas arquiteturais

### "Quero começar a desenvolver"
- **[STATUS.md](/STATUS.md)** - Status e checklist
- **[guidelines/Guidelines.md](/guidelines/Guidelines.md)** - Diretrizes
- **[CHANGELOG_ONNX.md](/CHANGELOG_ONNX.md)** - Mudanças recentes

### "Quero configurar inferência"
- **[SISTEMA_INFERENCIA.md](/SISTEMA_INFERENCIA.md)** - Como funciona a inferência
- **[INFERENCE_MODES.md](/INFERENCE_MODES.md)** - Modos disponíveis
- **[QUICKSTART_ONNX.md](/QUICKSTART_ONNX.md)** - Setup ONNX
- **[models/README.md](/models/README.md)** - Modelos e treinamento

### "Tenho um problema"
- **[TROUBLESHOOTING.md](/TROUBLESHOOTING.md)** - Resolução de problemas
- **[STATUS.md](/STATUS.md)** - Verificar status atual

### "Quero treinar um modelo"
- **[models/README.md](/models/README.md)** - Guia completo de treinamento
- **[convert_to_onnx.py](/convert_to_onnx.py)** - Script de conversão

---

## 📖 Documentação por Categoria

### 🏗️ Arquitetura

| Documento | Descrição | Quando usar |
|-----------|-----------|-------------|
| [diagrams/README.md](/diagrams/README.md) | Todos os diagramas | Entender arquitetura |
| [diagrams/INDEX.md](/diagrams/INDEX.md) | Índice dos diagramas | Navegação rápida |
| [diagrams/EXECUTIVE_SUMMARY.md](/diagrams/EXECUTIVE_SUMMARY.md) | Resumo executivo | Apresentações |
| [diagrams/architecture-diagram.puml](/diagrams/architecture-diagram.puml) | Diagrama de arquitetura | Ver componentes |
| [diagrams/class-diagram.puml](/diagrams/class-diagram.puml) | Diagrama de classes | Entender modelos |
| [diagrams/sequence-diagram.puml](/diagrams/sequence-diagram.puml) | Diagrama de sequência | Entender fluxos |
| [diagrams/database-diagram.puml](/diagrams/database-diagram.puml) | Diagrama do banco | Entender dados |

### 🧠 Inferência e IA

| Documento | Descrição | Quando usar |
|-----------|-----------|-------------|
| [SISTEMA_INFERENCIA.md](/SISTEMA_INFERENCIA.md) | Sistema de inferência | Entender como funciona |
| [INFERENCE_MODES.md](/INFERENCE_MODES.md) | Modos de operação | Escolher modo |
| [QUICKSTART_ONNX.md](/QUICKSTART_ONNX.md) | Guia rápido ONNX | Setup rápido |
| [models/README.md](/models/README.md) | Modelos e treinamento | Treinar/converter |
| [utils/onnxInference.tsx](/utils/onnxInference.tsx) | Código ONNX | Desenvolvimento |

### 🛠️ Desenvolvimento

| Documento | Descrição | Quando usar |
|-----------|-----------|-------------|
| [guidelines/Guidelines.md](/guidelines/Guidelines.md) | Diretrizes | Seguir padrões |
| [STRUCTURE.md](/STRUCTURE.md) | Estrutura do projeto | Localizar arquivos |
| [CHANGELOG_ONNX.md](/CHANGELOG_ONNX.md) | Mudanças ONNX | Ver o que mudou |
| [Attributions.md](/Attributions.md) | Atribuições | Créditos |

### 🔧 Operação e Suporte

| Documento | Descrição | Quando usar |
|-----------|-----------|-------------|
| [STATUS.md](/STATUS.md) | Status do sistema | Verificar saúde |
| [TROUBLESHOOTING.md](/TROUBLESHOOTING.md) | Resolução de problemas | Resolver erros |
| [README.md](/README.md) | Visão geral | Primeira leitura |

### 🗄️ Backend e Banco de Dados

| Documento | Descrição | Quando usar |
|-----------|-----------|-------------|
| [supabase/migrations/](/supabase/migrations/) | Migrations SQL | Setup do banco |
| [supabase/functions/server/](/supabase/functions/server/) | Edge Functions | Backend code |
| [diagrams/database-diagram.puml](/diagrams/database-diagram.puml) | Schema do banco | Entender estrutura |

---

## 📂 Estrutura de Diretórios

```
/
├── 📄 README.md                    ← Comece aqui
├── 📄 STATUS.md                    ← Status atual
├── 📄 TROUBLESHOOTING.md           ← Problemas?
├── 📄 SISTEMA_INFERENCIA.md        ← Como funciona IA
├── 📄 INFERENCE_MODES.md           ← Modos de inferência
├── 📄 QUICKSTART_ONNX.md           ← Setup rápido
├── 📄 PROJECT_GUIDE.md             ← Guia completo
├── 📄 STRUCTURE.md                 ← Estrutura de arquivos
├── 📄 CHANGELOG_ONNX.md            ← O que mudou
│
├── 📁 components/                  ← Componentes React
│   ├── CameraFeed.tsx             ← Feed de câmera + IA
│   ├── ConveyorSystem.tsx         ← Animação esteira
│   ├── GateConfiguration.tsx      ← Config cancelas
│   └── ... (outros componentes)
│
├── 📁 supabase/                    ← Backend
│   ├── functions/server/          ← Edge Functions
│   │   ├── index.tsx              ← Servidor principal
│   │   ├── Autenticacao.tsx       ← Classes de autenticação
│   │   └── ... (outras classes)
│   └── migrations/                ← SQL migrations
│
├── 📁 utils/                       ← Utilitários
│   ├── onnxInference.tsx          ← ONNX Runtime
│   └── supabase/                  ← Cliente Supabase
│
├── 📁 models/                      ← Modelos YOLO
│   └── README.md                  ← Guia de modelos
│
├── 📁 diagrams/                    ← Diagramas
│   ├── README.md                  ← Índice
│   ├── *.puml                     ← Arquivos PlantUML
│   └── ... (diagramas)
│
├── 📁 guidelines/                  ← Diretrizes
│   └── Guidelines.md              ← Padrões de código
│
├── 🐍 inference_server.py          ← Servidor Python (opcional)
├── 🐍 convert_to_onnx.py           ← Converter YOLO → ONNX
├── 🐍 test_setup.py                ← Testar setup
└── 📄 requirements.txt             ← Deps Python
```

---

## 🎯 Fluxos de Leitura Recomendados

### Fluxo 1: "Quero entender tudo"
1. README.md
2. STATUS.md
3. PROJECT_GUIDE.md
4. SISTEMA_INFERENCIA.md
5. diagrams/README.md
6. STRUCTURE.md

### Fluxo 2: "Quero começar rápido"
1. STATUS.md (checklist)
2. QUICKSTART_ONNX.md
3. TROUBLESHOOTING.md (referência)

### Fluxo 3: "Quero desenvolver"
1. guidelines/Guidelines.md
2. STRUCTURE.md
3. diagrams/architecture-diagram.puml
4. supabase/functions/server/index.tsx

### Fluxo 4: "Quero resolver um erro"
1. TROUBLESHOOTING.md
2. STATUS.md (verificar status)
3. Logs do navegador (F12)
4. SISTEMA_INFERENCIA.md (se erro de IA)

### Fluxo 5: "Quero treinar um modelo"
1. models/README.md
2. convert_to_onnx.py
3. QUICKSTART_ONNX.md
4. test_setup.py

---

## 🔍 Busca Rápida

### Por Tópico

**Autenticação:**
- supabase/functions/server/Autenticacao.tsx
- components/Login.tsx
- STATUS.md (seção Autenticação)

**Câmera e Inferência:**
- components/CameraFeed.tsx
- utils/onnxInference.tsx
- SISTEMA_INFERENCIA.md
- INFERENCE_MODES.md

**Configurações:**
- components/GateConfiguration.tsx
- components/AccuracyControl.tsx
- supabase/functions/server/index.tsx (rotas /config)

**Esteira e Animação:**
- components/ConveyorSystem.tsx
- diagrams/sequence-diagram.puml

**Estatísticas:**
- components/StatisticsPanel.tsx
- components/MonitorPanel.tsx
- supabase/functions/server/index.tsx (rotas /stats)

**Banco de Dados:**
- supabase/migrations/001_create_ecovision_tables.sql
- diagrams/database-diagram.puml
- supabase/functions/server/BancoDeDados.tsx

**Modelos YOLO:**
- models/README.md
- convert_to_onnx.py
- inference_server.py

---

## 📊 Referências Rápidas

### Classes do Backend
```typescript
// Localizadas em: /supabase/functions/server/
- Autenticacao.tsx      - Gerenciamento de auth
- BancoDeDados.tsx      - Conexão DB
- Camera.tsx            - Gerenciamento de câmeras
- Cancela.tsx           - Controle de cancelas
- Esteira.tsx           - Controle da esteira
- ModeloIA.tsx          - Integração com IA
- Usuario.tsx           - Gerenciamento de usuários
- RegistroProcessamento.tsx - Logs de processamento
- Dashboard.tsx         - Agregação de dados
- OutputData.tsx        - Formatação de respostas
```

### Componentes Principais
```typescript
// Localizados em: /components/
- App.tsx              - App principal
- Sidebar.tsx          - Menu lateral
- Login.tsx            - Tela de login
- CameraFeed.tsx       - Feed de câmera + IA
- ConveyorSystem.tsx   - Animação da esteira
- GateConfiguration.tsx - Config de cancelas
- AccuracyControl.tsx  - Controle de precisão
- StatisticsPanel.tsx  - Estatísticas
- MonitorPanel.tsx     - Monitoramento
- UserProfile.tsx      - Perfil do usuário
```

### Rotas da API
```
GET  /make-server-ea835390/health        - Health check
GET  /make-server-ea835390/auth-test     - Teste de auth
POST /make-server-ea835390/config        - Salvar config
GET  /make-server-ea835390/config        - Obter config
POST /make-server-ea835390/inference     - Inferência
GET  /make-server-ea835390/stats         - Estatísticas
GET  /make-server-ea835390/stats/period  - Stats por período
POST /make-server-ea835390/session/end   - Encerrar sessão
POST /make-server-ea835390/logs          - Salvar log
GET  /make-server-ea835390/logs          - Obter logs
GET  /make-server-ea835390/user/stats    - Stats do usuário
```

---

## 🆕 Atualizações Recentes

**Última atualização:** 09/Nov/2025

**O que mudou:**
- ✅ Resolvido erro Connection Refused
- ✅ Sistema híbrido ONNX + Python
- ✅ Documentação completa criada
- ✅ Guias de troubleshooting
- ✅ Scripts de conversão

**Ver detalhes em:**
- [CHANGELOG_ONNX.md](/CHANGELOG_ONNX.md)
- [STATUS.md](/STATUS.md)

---

## 💡 Dicas de Navegação

1. **Use Ctrl+F** para buscar palavras-chave neste índice
2. **Comece pelo STATUS.md** para overview atual
3. **Use TROUBLESHOOTING.md** como referência
4. **Consulte diagramas** para entender visualmente
5. **Leia os comentários** no código fonte

---

**📌 Favoritos Recomendados:**
- STATUS.md
- TROUBLESHOOTING.md
- SISTEMA_INFERENCIA.md
- models/README.md

**Última atualização:** 09/Nov/2025
