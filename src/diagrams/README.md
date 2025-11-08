# Diagramas do EcoVision

Este diretório contém os diagramas UML do sistema EcoVision em formato PlantUML (.puml).

## Arquivos Disponíveis

### 1. `class-diagram.puml` - Diagrama de Classes
Mostra a estrutura completa de classes do sistema, incluindo:
- **Frontend (React Components)**: App, Login, MonitorPanel, CameraFeed, ConveyorSystem, GateConfiguration, AccuracyControl, StatisticsPanel, UserProfile
- **Backend (Server)**: HonoServer e seus endpoints REST
- **Domain (Models)**: Camera, Esteira, Cancela, ModeloIA, ControladorSerial, OutputData, BancoDeDados, Dashboard, Autenticacao, Usuario, RegistroProcessamento
- **Infrastructure**: SupabaseClient, KeyValueStore
- Relacionamentos e dependências entre todas as classes

### 2. `sequence-diagram.puml` - Diagramas de Sequência
Contém 5 fluxos principais de interação:
1. **Fluxo de Autenticação**: Login com Google OAuth e modo demo
2. **Fluxo de Configuração do Sistema**: Configuração de cancelas e calibração de confiança
3. **Fluxo de Monitoramento e Detecção**: Processo completo de detecção com IA, acionamento de cancelas e registro
4. **Fluxo de Visualização de Estatísticas**: Consulta e exibição de dados do dashboard
5. **Fluxo de Logout**: Encerramento de sessão

### 3. `architecture-diagram.puml` - Arquitetura de Três Camadas
Visualiza a arquitetura completa do sistema:
- **Camada 1 - Frontend**: Componentes React, hooks e utilidades
- **Camada 2 - Server**: Edge Functions, modelos de domínio e API REST
- **Camada 3 - Database**: PostgreSQL, Supabase Auth e Storage
- **Hardware Externo**: ESP32, webcam, servidor de inferência Python e atuadores físicos

### 4. `data-flow-diagram.puml` - Fluxo de Dados em Tempo Real
Mostra o fluxo completo de dados desde a captura até a ação:
- **Entrada**: Webcam capturando vídeo da esteira
- **Processamento Frontend**: Loop de detecção a cada 3 segundos
- **Inferência IA**: Predição YOLO com bounding boxes
- **Lógica de Decisão**: Verificação de confiança e matching com cancelas
- **Acionamento**: Controle serial do ESP32 e servos
- **Persistência**: Registro em banco de dados
- **Feedback Visual**: Canvas overlay e notificações
- **Métricas e Timings**: Performance e tempos de resposta

### 5. `component-diagram.puml` - Diagrama de Componentes React
Detalha a estrutura de componentes React com props e estado:
- **Hierarquia de Componentes**: App → Abas → Subcomponentes
- **Props Flow**: Passagem de dados entre componentes pai e filho
- **Estado Local**: State hooks de cada componente
- **Uso de Shadcn/UI**: Integração com componentes de UI
- **Hooks e Utilitários**: SupabaseClient, API helpers
- **Layout Responsivo**: Estrutura de duas colunas do MonitorPanel

### 6. `database-diagram.puml` - Diagrama de Banco de Dados
Documenta o modelo de dados completo do PostgreSQL:
- **Tabelas Principais**: profiles, user_sessions, inferences, system_config, statistics, system_logs
- **Supabase Auth**: Integração com auth.users (gerenciado)
- **Relacionamentos**: Foreign keys e constraints
- **Índices**: Otimizações de performance
- **Triggers e Functions**: Automações do banco
- **Views**: Consultas pré-definidas para dashboard
- **RLS (Row Level Security)**: Políticas de segurança por usuário

## Como Visualizar os Diagramas

### Opção 1: Visual Studio Code (Recomendado)
1. Instale a extensão **PlantUML** por jebbs
2. Instale o **Graphviz** no seu sistema:
   - **Windows**: `choco install graphviz` ou baixe de https://graphviz.org/download/
   - **macOS**: `brew install graphviz`
   - **Linux**: `sudo apt-get install graphviz`
3. Abra qualquer arquivo `.puml` no VS Code
4. Pressione `Alt+D` (Windows/Linux) ou `Option+D` (macOS) para visualizar
5. Ou clique com botão direito e selecione "Preview Current Diagram"

### Opção 2: PlantUML Online
1. Acesse http://www.plantuml.com/plantuml/uml/
2. Copie o conteúdo de qualquer arquivo `.puml`
3. Cole na interface web
4. Visualize o diagrama renderizado

### Opção 3: IntelliJ IDEA / PyCharm
1. Instale o plugin **PlantUML Integration**
2. Abra qualquer arquivo `.puml`
3. A prévia será exibida automaticamente no painel lateral

### Opção 4: Exportar para PNG/SVG via CLI
```bash
# Instale o PlantUML
sudo apt-get install plantuml  # Linux
brew install plantuml           # macOS

# Gere imagens PNG
plantuml diagrams/class-diagram.puml
plantuml diagrams/sequence-diagram.puml
plantuml diagrams/architecture-diagram.puml
plantuml diagrams/data-flow-diagram.puml
plantuml diagrams/component-diagram.puml
plantuml diagrams/database-diagram.puml

# Ou gere SVG (melhor qualidade)
plantuml -tsvg diagrams/class-diagram.puml
plantuml -tsvg diagrams/sequence-diagram.puml
plantuml -tsvg diagrams/architecture-diagram.puml
plantuml -tsvg diagrams/data-flow-diagram.puml
plantuml -tsvg diagrams/component-diagram.puml
plantuml -tsvg diagrams/database-diagram.puml

# Gerar todos de uma vez
plantuml diagrams/*.puml
plantuml -tsvg diagrams/*.puml
```

## Estrutura dos Diagramas

### Cores Utilizadas

Os diagramas seguem a paleta de cores do EcoVision:

- **Verde Principal** (#034732 a #ABF2AB): Elementos gerais do sistema
- **Azul Papel** (#163B6F): Papel/Papelão
- **Verde Metal** (#196626): Metal
- **Vermelho Plástico** (#DC1F2E): Plástico
- **Amarelo Vidro** (#D2B91F): Vidro

### Convenções de Nomenclatura

- **Classes**: PascalCase (ex: `ModeloIA`, `ControladorSerial`)
- **Métodos**: camelCase (ex: `preverFrame()`, `decidirAcionamento()`)
- **Atributos**: camelCase (ex: `minAccuracy`, `isSystemRunning`)
- **Componentes React**: PascalCase (ex: `MonitorPanel`, `CameraFeed`)

## Atualização dos Diagramas

Quando houver mudanças no código, atualize os diagramas correspondentes:

1. **Novas classes ou componentes**: Adicione ao `class-diagram.puml`
2. **Novos fluxos de interação**: Adicione ao `sequence-diagram.puml`
3. **Mudanças na arquitetura**: Atualize o `architecture-diagram.puml`

## Recursos Adicionais

- [Documentação PlantUML](https://plantuml.com/)
- [Guia de Diagramas de Classe](https://plantuml.com/class-diagram)
- [Guia de Diagramas de Sequência](https://plantuml.com/sequence-diagram)
- [Sintaxe PlantUML](https://plantuml.com/guide)

## Integração com Documentação

Estes diagramas complementam a documentação do projeto:
- `API.md` - Documentação da API REST
- `README.md` - Visão geral do projeto
- `SETUP.md` - Instruções de configuração
- `guidelines/Guidelines.md` - Diretrizes de desenvolvimento
