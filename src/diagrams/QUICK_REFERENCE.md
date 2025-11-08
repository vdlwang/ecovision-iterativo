# 🚀 Referência Rápida - Diagramas EcoVision

Guia rápido de consulta para encontrar informações específicas nos diagramas.

---

## 🔍 "Onde Encontro...?"

### Frontend / React

| Preciso Saber... | Veja | Arquivo |
|------------------|------|---------|
| Estrutura de componentes React | Componentes React | `component-diagram.puml` |
| Props de um componente | Componentes React | `component-diagram.puml` |
| Estado (useState) de um componente | Componentes React | `component-diagram.puml` |
| Componentes Shadcn/UI usados | Componentes React | `component-diagram.puml` |
| Fluxo de login/autenticação | Sequência → Fluxo 1 | `sequence-diagram.puml` |
| Como a câmera detecta objetos | Sequência → Fluxo 3 | `sequence-diagram.puml` |
| Timing do loop de detecção | Fluxo de Dados | `data-flow-diagram.puml` |

### Backend / Server

| Preciso Saber... | Veja | Arquivo |
|------------------|------|---------|
| Endpoints da API | Arquitetura (notas) | `architecture-diagram.puml` |
| Classes de domínio | Classes | `class-diagram.puml` |
| Como o modelo IA funciona | Classes → ModeloIA | `class-diagram.puml` |
| Fluxo de processamento | Sequência → Fluxo 3 | `sequence-diagram.puml` |
| Controle serial do ESP32 | Classes → ControladorSerial | `class-diagram.puml` |
| Decisão de acionamento | Fluxo de Dados → Decisão | `data-flow-diagram.puml` |

### Database / Persistência

| Preciso Saber... | Veja | Arquivo |
|------------------|------|---------|
| Estrutura do banco | Banco de Dados | `database-diagram.puml` |
| Tabelas e colunas | Banco de Dados | `database-diagram.puml` |
| Como salvar detecções | Banco de Dados → inferences | `database-diagram.puml` |
| Relacionamentos entre tabelas | Banco de Dados | `database-diagram.puml` |
| Constraints e índices | Banco de Dados (notas) | `database-diagram.puml` |
| Triggers e functions | Banco de Dados → Functions | `database-diagram.puml` |
| Views para dashboard | Banco de Dados → Views | `database-diagram.puml` |
| Row Level Security | Banco de Dados (notas RLS) | `database-diagram.puml` |
| Chaves do KV Store | Fluxo de Dados (notas) | `data-flow-diagram.puml` |
| Consultas de estatísticas | Sequência → Fluxo 4 | `sequence-diagram.puml` |

### Hardware / IoT

| Preciso Saber... | Veja | Arquivo |
|------------------|------|---------|
| Conexão com ESP32 | Arquitetura → Hardware | `architecture-diagram.puml` |
| Comandos seriais | Fluxo de Dados (notas) | `data-flow-diagram.puml` |
| Protocolo de comunicação | Arquitetura (notas) | `architecture-diagram.puml` |
| Acionamento de cancelas | Sequência → Fluxo 3 | `sequence-diagram.puml` |
| Timing de abertura/fechamento | Fluxo de Dados | `data-flow-diagram.puml` |

---

## 📊 "Como Funciona...?"

### Fluxos de Usuário

| Funcionalidade | Diagrama | Localização |
|----------------|----------|-------------|
| **Login com Google** | Sequência | Fluxo 1: Autenticação |
| **Configurar cancelas** | Sequência | Fluxo 2: Configuração (parte 1) |
| **Ajustar confiança** | Sequência | Fluxo 2: Configuração (parte 2) |
| **Iniciar sistema** | Sequência | Fluxo 3: Monitoramento (início) |
| **Detecção em tempo real** | Sequência + Fluxo de Dados | Fluxo 3 + data-flow completo |
| **Ver estatísticas** | Sequência | Fluxo 4: Dashboard |
| **Fazer logout** | Sequência | Fluxo 5: Logout |

### Processos Técnicos

| Processo | Melhor Diagrama | Por Quê |
|----------|-----------------|---------|
| **Captura de vídeo** | Fluxo de Dados | Mostra entrada → processamento → saída |
| **Inferência YOLO** | Sequência + Fluxo de Dados | Mostra chamadas + decisões |
| **Acionamento de cancela** | Todos os 3 | Classes (estrutura), Sequência (fluxo), Dados (timing) |
| **Registro no banco** | Sequência + Classes | Mostra fluxo + estrutura de dados |
| **Atualização de gráficos** | Sequência + Componentes | Mostra consulta + renderização |

---

## 🎯 "Preciso Modificar..."

### Mudanças no Frontend

| Mudança | Consulte | Para Entender |
|---------|----------|---------------|
| Adicionar nova aba | Componentes React → App.tsx | Estrutura de tabs e roteamento |
| Modificar props de componente | Componentes React | Hierarquia e passagem de dados |
| Adicionar novo gráfico | Componentes React → StatsPanel | Integração com Recharts |
| Mudar layout do Monitor | Componentes React → MonitorPanel | Estrutura de 2 colunas |
| Adicionar validação | Componentes React → GateConfig | Lógica de validação existente |

### Mudanças no Backend

| Mudança | Consulte | Para Entender |
|---------|----------|---------------|
| Adicionar endpoint | Arquitetura + Sequência | Onde adicionar + como implementar |
| Nova classe de domínio | Classes | Padrões de design e relacionamentos |
| Modificar modelo IA | Classes → ModeloIA | Métodos e responsabilidades |
| Alterar protocolo serial | Classes → ControladorSerial | Implementação atual |
| Nova consulta ao banco | Classes → BancoDeDados | Métodos disponíveis |

### Mudanças no Hardware

| Mudança | Consulte | Para Entender |
|---------|----------|---------------|
| Novo comando serial | Fluxo de Dados (notas) | Formato atual de comandos |
| Adicionar cancela | Arquitetura + Classes | Estrutura atual de cancelas |
| Mudar baud rate | Classes → ControladorSerial | Configuração serial |
| Novo sensor | Arquitetura → Hardware | Onde integrar novo hardware |

---

## ⏱️ "Qual o Timing de...?"

| Operação | Tempo | Onde Está |
|----------|-------|-----------|
| Loop de detecção | 3 segundos | Fluxo de Dados (DetectionLoop) |
| Acionamento de cancela | 2 segundos | Fluxo de Dados (Acionamento) |
| FPS da webcam | 30 fps | Fluxo de Dados (Webcam) |
| Atualização do dashboard | 10 segundos | Componentes React → StatsPanel |
| Timeout de sessão | - | (não implementado) |
| Delay pós-detecção | 0ms | Imediato após inferência |

---

## 🔗 "Qual a Relação Entre...?"

### Componentes e Classes

| Frontend | Backend | Relacionamento |
|----------|---------|----------------|
| `CameraFeed` | `ModeloIA` | CameraFeed chama ModeloIA via API |
| `ConveyorSystem` | `Esteira` | ConveyorSystem controla Esteira via API |
| `GateConfiguration` | `Cancela` | GateConfig salva configs para Cancelas |
| `AccuracyControl` | `ModeloIA` | AccuracyCtrl calibra limites do ModeloIA |
| `StatisticsPanel` | `Dashboard` | StatsPanel exibe dados do Dashboard |

### Classes entre Si

| Classe A | Classe B | Relacionamento |
|----------|----------|----------------|
| `ModeloIA` | `ControladorSerial` | ModeloIA usa ControladorSerial (composição) |
| `Esteira` | `ControladorSerial` | Esteira usa ControladorSerial (composição) |
| `Cancela` | `ControladorSerial` | Cancela usa ControladorSerial (composição) |
| `ModeloIA` | `BancoDeDados` | ModeloIA registra em BancoDeDados |
| `Dashboard` | `BancoDeDados` | Dashboard consulta BancoDeDados |
| `ControladorSerial` | `IAtuador` | ControladorSerial implementa IAtuador |

---

## 🐛 "Como Debugar...?"

### Problemas Comuns

| Problema | Diagnóstico | Diagrama |
|----------|-------------|----------|
| **Câmera não detecta** | Verifique loop + endpoint + modelo | Sequência Fluxo 3 + Fluxo de Dados |
| **Cancela não abre** | Verifique decisão + serial | Fluxo de Dados (Decisão + Serial) |
| **Stats não atualizam** | Verifique polling + endpoint | Sequência Fluxo 4 + Componentes |
| **Login falha** | Verifique OAuth + sessão | Sequência Fluxo 1 |
| **Config não salva** | Verifique endpoint + KV Store | Sequência Fluxo 2 |

### Pontos de Falha

| Camada | Ponto Crítico | Verificar em |
|--------|---------------|--------------|
| Frontend | Loop de detecção não inicia | Componentes React → CameraFeed |
| API | Endpoint não responde | Arquitetura → Server API |
| Backend | Modelo IA não carregado | Classes → ModeloIA |
| Serial | ESP32 desconectado | Classes → ControladorSerial |
| Database | KV Store indisponível | Arquitetura → Database |

---

## 📐 "Quais São os Limites...?"

| Parâmetro | Valor | Onde Configurar |
|-----------|-------|-----------------|
| Confiança mínima | 50-100% (padrão: 85%) | AccuracyControl |
| Número de cancelas | 3 (fixo) | GateConfiguration |
| FPS da câmera | 30 fps | CameraFeed |
| Frequência de detecção | 3 segundos | CameraFeed |
| Tempo de acionamento | 2 segundos | ModeloIA |
| Modelos YOLO | n, s, m | AccuracyControl |
| Materiais | papel, metal, plastico, vidro | Sistema |

---

## 🔐 "Onde Está a Segurança...?"

| Aspecto | Implementação | Diagrama |
|---------|---------------|----------|
| **Autenticação** | Google OAuth via Supabase | Sequência Fluxo 1 |
| **Autorização** | Session tokens | Classes → Autenticacao |
| **API Security** | Bearer token no header | Arquitetura (notas) |
| **CORS** | Configurado no Hono | Arquitetura → Server |
| **Env Variables** | SUPABASE_* keys | Arquitetura (notas) |

---

## 📦 "Onde Adicionar...?"

### Nova Feature

| Tipo de Feature | Adicione em | Atualize Diagrama |
|-----------------|-------------|-------------------|
| **Nova aba** | App.tsx + novo componente | Componentes React |
| **Novo endpoint** | server/index.tsx | Arquitetura + Sequência |
| **Nova classe** | server/models.tsx | Classes |
| **Novo material** | Sistema (cores + configs) | Todos |
| **Novo hardware** | ControladorSerial | Arquitetura + Classes |

---

## 🎨 Legenda Visual Rápida

```
🟢 Verde    = Sistema EcoVision / Frontend
🔵 Azul     = Database / Backend
🔴 Vermelho = Importante / Crítico
🟡 Amarelo  = Hardware / Externo
🟠 Laranja  = API / Server
⚪ Branco   = Genérico / Utilitário
```

---

## 💡 Atalhos Úteis

| Para... | Vá Direto Para |
|---------|----------------|
| Entender o sistema todo | `architecture-diagram.puml` |
| Ver fluxo completo de detecção | `sequence-diagram.puml` (Fluxo 3) |
| Trabalhar no frontend | `component-diagram.puml` |
| Trabalhar no backend | `class-diagram.puml` |
| Otimizar performance | `data-flow-diagram.puml` |

---

## 📞 Suporte

- **Dúvidas sobre diagramas**: Consulte [README.md](./README.md)
- **Dúvidas sobre código**: Consulte código-fonte + comentários
- **Dúvidas sobre API**: Consulte [../API.md](../API.md)
- **Dúvidas sobre setup**: Consulte [../SETUP.md](../SETUP.md)

---

*Este é um documento vivo. Atualize conforme o sistema evolui!*
