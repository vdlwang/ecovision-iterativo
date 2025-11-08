# EcoVision - Sistema de Controle Inteligente para Centro de Reciclagem

![EcoVision Logo](https://img.shields.io/badge/EcoVision-Sistema%20de%20Reciclagem-008148?style=for-the-badge&logo=recycle)

## 📋 Sobre o Projeto

O **EcoVision** é um sistema de controle inteligente para esteiras de centros de reciclagem, integrado com modelos de Inteligência Artificial para identificação e separação automática de materiais recicláveis.

O sistema utiliza câmeras em tempo real e modelos YOLO (You Only Look Once) para detectar e classificar materiais (papel/papelão, metal, plástico e vidro), acionando cancelas automaticamente para separar os resíduos de forma eficiente.

### 🎯 Funcionalidades Principais

- **Monitoramento em Tempo Real**: Visualização de câmeras e status da esteira
- **Detecção Inteligente**: Modelos YOLOv8 (nano, small, medium) para classificação de materiais
- **Controle de Cancelas**: Configuração de até 3 cancelas para separação automática
- **Ajuste de Acurácia**: Controle do limiar mínimo de confiança para aceitar detecções
- **Dashboard de Estatísticas**: Visualização de performance e métricas do sistema
- **Painel de Testes**: Testes manuais e visualização de logs do sistema
- **Autenticação Google**: Login seguro via OAuth 2.0

## 🏗️ Arquitetura do Sistema

### Frontend
- **React**: Framework UI
- **TypeScript**: Tipagem estática
- **Tailwind CSS**: Estilização
- **Shadcn/UI**: Componentes de interface
- **Recharts**: Visualização de dados

### Backend
- **Supabase**: Backend-as-a-Service
- **PostgreSQL**: Banco de dados
- **Deno + Hono**: Edge functions para API
- **Supabase Auth**: Autenticação e autorização

### IA/ML
- **YOLOv8**: Modelos de detecção de objetos
  - YOLOv8n (nano): Mais rápido, menor precisão
  - YOLOv8s (small): Balanceado
  - YOLOv8m (medium): Mais preciso, mais lento

## 📦 Estrutura do Projeto

```
ecovision/
├── components/              # Componentes React
│   ├── ui/                 # Componentes de UI (Shadcn)
│   ├── AccuracyControl.tsx # Controle de acurácia e modelo
│   ├── ConveyorSystemCompact.tsx # Sistema de esteira
│   ├── GateConfiguration.tsx     # Configuração de cancelas
│   ├── Login.tsx                 # Tela de login
│   ├── Sidebar.tsx              # Menu lateral
│   ├── StatisticsPanel.tsx      # Dashboard de estatísticas
│   └── TestPanel.tsx            # Painel de testes
├── supabase/
│   └── functions/
│       └── server/
│           ├── index.tsx        # API do servidor
│           └── kv_store.tsx     # Armazenamento KV
├── styles/
│   └── globals.css              # Estilos globais
├── utils/
│   └── supabase/
│       └── info.tsx             # Configuração Supabase
├── App.tsx                      # Componente principal
└── README.md                    # Este arquivo
```

## 🚀 Como Rodar Localmente

### Pré-requisitos

- Node.js 18+ instalado
- Conta no Supabase (gratuita)
- Git instalado

### 1. Clonar o Repositório

```bash
git clone <seu-repositorio>
cd ecovision
```

### 2. Configurar o Supabase

1. Acesse [supabase.com](https://supabase.com) e crie uma conta
2. Crie um novo projeto
3. Anote o **Project URL** e a **Anon Key** do seu projeto

#### ⚠️ IMPORTANTE: Configurar Google OAuth (Obrigatório para Login)

**Se você receber o erro `"provider is not enabled"`, siga estes passos:**

4. Acesse o [Google Cloud Console](https://console.cloud.google.com)
5. Crie um novo projeto ou selecione um existente
6. Ative a **Google+ API**:
   - Menu lateral > APIs & Services > Library
   - Procure por "Google+ API"
   - Clique em "Enable"
7. Crie credenciais OAuth 2.0:
   - Menu lateral > APIs & Services > Credentials
   - Clique em "Create Credentials" > "OAuth client ID"
   - Tipo: Web application
   - Nome: EcoVision
   - Authorized JavaScript origins:
     - `http://localhost:5173` (desenvolvimento)
     - `https://seu-dominio.com` (produção)
   - Authorized redirect URIs:
     - `https://seu-projeto.supabase.co/auth/v1/callback`
   - Clique em "Create"
   - Copie o **Client ID** e **Client Secret**

8. Volte ao Supabase:
   - **Authentication > Providers > Google**
   - Habilite o Google
   - Cole o **Client ID** e **Client Secret**
   - **Site URL**: `http://localhost:5173` (desenvolvimento)
   - **Redirect URLs**: 
     - `http://localhost:5173/**`
     - `https://seu-dominio.com/**` (produção)
   - Clique em "Save"

#### 🧪 Modo Demo (Alternativa para Teste)

Se você não quiser configurar o Google OAuth imediatamente, pode usar o **Modo Demo**:
- Na tela de login, clique em "Entrar em Modo Demo"
- Isso permite testar todas as funcionalidades sem autenticação real
- **Nota**: O modo demo não persiste dados entre sessões

### 3. Configurar Variáveis de Ambiente

O projeto já está integrado com Supabase. Você precisará apenas garantir que os valores em `utils/supabase/info.tsx` estejam corretos:

```typescript
export const projectId = "seu-project-id";
export const publicAnonKey = "sua-anon-key";
```

### 4. Instalar Dependências

```bash
npm install
```

### 5. Executar em Desenvolvimento

```bash
npm run dev
```

O aplicativo estará disponível em `http://localhost:5173`

## 🔑 Autenticação

O sistema utiliza autenticação Google OAuth via Supabase:

1. **Primeira vez**: Clique em "Entrar com Google"
2. Autorize o aplicativo na sua conta Google
3. Você será redirecionado de volta ao sistema
4. Suas credenciais são armazenadas de forma segura pelo Supabase

### Configurar Google OAuth

Para configurar a autenticação Google, você precisa:

1. Criar um projeto no [Google Cloud Console](https://console.cloud.google.com)
2. Habilitar a Google+ API
3. Criar credenciais OAuth 2.0
4. Adicionar as credenciais no Supabase (Authentication > Providers > Google)

**📚 Tutorial completo**: https://supabase.com/docs/guides/auth/social-login/auth-google

## 🏛️ Arquitetura Backend (Modelo de Classes)

O backend foi implementado seguindo um modelo orientado a objetos com as seguintes classes:

### Classes Principais

#### 📹 **Camera**
Gerencia captura de vídeo e imagens
- `fps`: Taxa de frames por segundo
- `cap`: Objeto VideoCapture
- `resolucao`: Resolução da câmera
- Métodos: `iniciarStream()`, `capturarImagem()`, `pararStream()`, `is_ativa()`

#### 👤 **Usuario**
Gerencia informações do usuário autenticado
- `id`: ID único do usuário
- `name`: Nome do usuário
- `email`: Email do usuário
- `autenticado`: Status de autenticação
- Métodos: `to_dict()`

#### 🤖 **ModeloIA**
Gerencia o modelo YOLO e decisões de acionamento
- `nome`: Nome do modelo
- `versao`: Versão do modelo (n, s, m)
- `ativo`: Status do modelo
- `limiteMinAccuracy`: Limite mínimo de acurácia
- `model`: Instância do modelo YOLO
- `db`: Referência ao banco de dados
- `atuador`: Referência ao controlador de hardware
- Métodos: `ativar()`, `desativar()`, `carregarModelo()`, `preverFrame()`, `calibrarLimite()`, `decidirAcionamento()`, `executarAcionamento()`

#### 📊 **Dashboard**
Gerencia visualização de dados e métricas
- `db`: Referência ao banco de dados
- Métodos: `coletarVisaoGeral()`, `exibirStatusGeral()`, `exibirMateriaisReciclados()`, `exibirPerformanceCancelas()`

#### 🔐 **Autenticacao**
Gerencia autenticação de usuários
- `google_client_id`: ID do cliente Google OAuth
- `_sessions`: Mapa de sessões ativas
- Métodos: `loginComGoogle()`, `logout()`, `logout_try()`, `is_autenticado()`

#### 💾 **BancoDeDados**
Gerencia persistência de dados
- Métodos: `registrarProcessamento()`, `consultarItensProcessados()`, `consultarMateriais()`, `consultarPerformanceCancelas()`, `consultarPrecisaoMedia()`

#### ⚙️ **ControladorSerial**
Implementa interface com hardware via porta serial
- `portaSerial`: Porta serial (ex: /dev/ttyUSB0)
- `baudRate`: Taxa de comunicação (padrão: 9600)
- `ser`: Objeto serial
- Métodos: `conectar()`, `enviarComando()`, `ligarEsteira()`, `desligarEsteira()`, `abrirCancela()`, `fecharCancela()`

##### 🔌 Comandos Seriais Enviados

O sistema envia os seguintes comandos para a porta serial do dispositivo:

- `LIGAR_ESTEIRA`: Liga a esteira rolante
- `DESLIGAR_ESTEIRA`: Desliga a esteira rolante
- `ABRIR_CANCELA_1`: Abre a cancela 1
- `ABRIR_CANCELA_2`: Abre a cancela 2
- `ABRIR_CANCELA_3`: Abre a cancela 3
- `FECHAR_CANCELA_1`: Fecha a cancela 1
- `FECHAR_CANCELA_2`: Fecha a cancela 2
- `FECHAR_CANCELA_3`: Fecha a cancela 3

##### ⚙️ Configuração da Porta Serial

Por padrão, o sistema usa `/dev/ttyUSB0` como porta serial. Para alterar, defina a variável de ambiente:

```bash
SERIAL_PORT=/dev/ttyUSB1  # ou sua porta serial
```

**Nota**: Se a porta serial não estiver disponível, o sistema funciona em modo simulação, registrando os comandos no console.

#### 🎚️ **Esteira**
Representa a esteira rolante
- `status`: Status atual (ligada/desligada)
- `velocidade`: Velocidade da esteira
- `controlador`: Referência ao ControladorSerial
- Métodos: `ligar()`, `desligar()`

#### 🚪 **Cancela**
Representa uma cancela de separação
- `cancela_id`: ID da cancela (1, 2 ou 3)
- `status`: Status atual (aberta/fechada)
- `controlador`: Referência ao ControladorSerial
- Métodos: `abrir()`, `fechar()`

#### 📦 **OutputData**
Representa resultado de uma detecção do modelo
- `classePrevista`: Material detectado
- `confianca`: Confiança da detecção (0-100%)
- Métodos: `getClasse()`, `getConfianca()`

#### 📝 **RegistroProcessamento**
Representa um registro no banco de dados
- `id`: ID único do registro
- `material`: Material processado
- `precisao`: Precisão da detecção
- `cancela_id`: ID da cancela que processou
- `data`: Data/hora do processamento
- Métodos: `toJSON()`

### 📊 Diagramas UML

O projeto inclui documentação visual completa através de diagramas UML na pasta `/diagrams`:

- **📦 Diagrama de Classes** - Estrutura completa de classes e relacionamentos
- **🔄 Diagrama de Sequência** - 5 fluxos principais de interação
- **🏗️ Diagrama de Arquitetura** - Arquitetura de três camadas
- **📊 Diagrama de Fluxo de Dados** - Fluxo de dados em tempo real
- **🧩 Diagrama de Componentes React** - Estrutura de componentes e props

**📁 Acesse**: [/diagrams/INDEX.md](./diagrams/INDEX.md) para documentação completa dos diagramas

**🚀 Quick Reference**: [/diagrams/QUICK_REFERENCE.md](./diagrams/QUICK_REFERENCE.md) para guia de referência rápida

O sistema segue estes diagramas para fornecer:
- Detecção inteligente de materiais
- Controle automático de cancelas
- Monitoramento em tempo real
- Persistência de dados
- Dashboard com métricas

## 🗄️ Banco de Dados

O sistema utiliza o banco de dados PostgreSQL do Supabase com uma estrutura de Key-Value Store para armazenar:

- **Configurações do sistema** (cancelas, acurácia, modelo)
- **Detecções em tempo real**
- **Logs do sistema**
- **Estatísticas de operação**
- **Registros de processamento**

### Estrutura de Dados

```typescript
// Configuração do Sistema
{
  gateConfigs: { 1: "papel", 2: "plastico", 3: "metal" },
  minAccuracy: 85,
  modelVersion: "YOLOv8n",
  updatedAt: "2025-01-19T..."
}

// Detecção
{
  material: "plastico",
  confidence: 92.5,
  gateAssigned: 2,
  timestamp: "2025-01-19T...",
  createdAt: "2025-01-19T..."
}

// Log
{
  type: "info" | "success" | "warning" | "error",
  message: "Material detectado",
  details: { ... },
  createdAt: "2025-01-19T..."
}
```

## 🎨 Paleta de Cores

### Cores do Sistema (Verde)
- **Primary**: `#008148` - Verde principal
- **Primary Dark**: `#02643d` - Verde escuro
- **Primary Darker**: `#034732` - Verde mais escuro
- **Accent**: `#48b86c` - Verde claro
- **Light**: `#90ee90` - Verde bem claro
- **Lighter**: `#abf2ab` - Verde clarinho

### Cores dos Materiais
- **Papel/Papelão**: `#163b6f` (Azul)
- **Metal**: `#196626` (Verde)
- **Plástico**: `#dc1f2e` (Vermelho vibrante)
- **Vidro**: `#d2b91f` (Amarelo/Dourado)

## 📡 API Endpoints

### Health Check
```
GET /make-server-ea835390/health
```

### Configurações
```
POST /make-server-ea835390/config
GET /make-server-ea835390/config
```

### Detecções
```
POST /make-server-ea835390/detections
```

### Estatísticas
```
GET /make-server-ea835390/stats
```

### Logs
```
POST /make-server-ea835390/logs
GET /make-server-ea835390/logs
```

### Controle da Esteira
```
POST /make-server-ea835390/esteira/ligar
POST /make-server-ea835390/esteira/desligar
```

### Controle das Cancelas
```
POST /make-server-ea835390/cancela/:id/abrir
POST /make-server-ea835390/cancela/:id/fechar
```

### Modelo IA
```
POST /make-server-ea835390/modelo/ativar
POST /make-server-ea835390/modelo/desativar
POST /make-server-ea835390/modelo/calibrar
POST /make-server-ea835390/modelo/processar
```

### Câmera
```
POST /make-server-ea835390/camera/iniciar
POST /make-server-ea835390/camera/parar
GET /make-server-ea835390/camera/capturar
```

## 🚢 Deploy (Publicação do Site/App)

### Pré-requisitos para Deploy

1. Código versionado no GitHub
2. Google OAuth configurado no Supabase
3. Domínio próprio (opcional, mas recomendado)

### Opção 1: Vercel (Recomendado) ⭐

**Vantagens**: Deploy automático, CDN global, SSL gratuito, fácil integração com GitHub

#### Passo a Passo:

1. **Preparar o Repositório**
   ```bash
   git init
   git add .
   git commit -m "Initial commit - EcoVision"
   git remote add origin https://github.com/seu-usuario/ecovision.git
   git push -u origin main
   ```

2. **Deploy na Vercel**
   - Acesse [vercel.com](https://vercel.com) e faça login com GitHub
   - Clique em "New Project"
   - Importe o repositório `ecovision`
   - Configure:
     - **Framework Preset**: Vite
     - **Build Command**: `npm run build`
     - **Output Directory**: `dist`
   - Clique em "Deploy"

3. **Configurar Variáveis de Ambiente** (se necessário)
   - Na dashboard do projeto, vá em "Settings > Environment Variables"
   - Adicione as variáveis necessárias

4. **Configurar Domínio Personalizado** (opcional)
   - Vá em "Settings > Domains"
   - Adicione seu domínio customizado
   - Configure DNS conforme instruções

5. **Atualizar URLs no Supabase**
   - No Supabase, vá em "Authentication > URL Configuration"
   - **Site URL**: `https://seu-dominio.vercel.app`
   - **Redirect URLs**: `https://seu-dominio.vercel.app/**`

6. **Atualizar Google OAuth**
   - No Google Cloud Console, adicione:
   - **Authorized JavaScript origins**: `https://seu-dominio.vercel.app`
   - **Authorized redirect URIs**: `https://seu-projeto.supabase.co/auth/v1/callback`

**URL Final**: `https://seu-dominio.vercel.app`

---

### Opção 2: Netlify

**Vantagens**: Interface amigável, formulários gratuitos, functions serverless

#### Passo a Passo:

1. **Preparar o Repositório** (mesmo do Vercel acima)

2. **Deploy na Netlify**
   - Acesse [netlify.com](https://netlify.com) e faça login
   - Clique em "Add new site > Import an existing project"
   - Conecte com GitHub e selecione o repositório
   - Configure:
     - **Build command**: `npm run build`
     - **Publish directory**: `dist`
   - Clique em "Deploy site"

3. **Configurar Variáveis de Ambiente**
   - Vá em "Site settings > Environment variables"
   - Adicione as variáveis necessárias

4. **Configurar Domínio**
   - Vá em "Domain settings"
   - Adicione domínio customizado ou use o fornecido pelo Netlify

5. **Atualizar URLs** (mesmo processo do Vercel)

**URL Final**: `https://seu-site.netlify.app`

---

### Opção 3: GitHub Pages (Gratuito, mas Limitado)

**Vantagens**: 100% gratuito, integrado com GitHub

**Limitações**: Apenas sites estáticos, sem variáveis de ambiente server-side

#### Passo a Passo:

1. **Instalar gh-pages**
   ```bash
   npm install --save-dev gh-pages
   ```

2. **Adicionar scripts ao package.json**
   ```json
   {
     "scripts": {
       "predeploy": "npm run build",
       "deploy": "gh-pages -d dist"
     }
   }
   ```

3. **Configurar base no vite.config**
   ```javascript
   export default {
     base: '/ecovision/'
   }
   ```

4. **Deploy**
   ```bash
   npm run deploy
   ```

5. **Ativar GitHub Pages**
   - Vá no repositório > Settings > Pages
   - Source: `gh-pages` branch
   - Salvar

**URL Final**: `https://seu-usuario.github.io/ecovision/`

---

### Opção 4: Render (Backend + Frontend)

**Vantagens**: Deploy de backend Node.js/Deno gratuito, banco de dados PostgreSQL

#### Passo a Passo:

1. Acesse [render.com](https://render.com)
2. Crie um "Static Site" para o frontend
3. Configure:
   - **Build Command**: `npm run build`
   - **Publish Directory**: `dist`
4. Deploy!

**URL Final**: `https://ecovision.onrender.com`

---

### 🔧 Checklist Pós-Deploy

Após fazer o deploy, verifique:

- [ ] Site está acessível pela URL
- [ ] Login com Google funciona
- [ ] Câmeras carregam corretamente
- [ ] Sistema pode ser iniciado/parado
- [ ] Cancelas podem ser configuradas
- [ ] Estatísticas são exibidas
- [ ] Não há erros no console do navegador
- [ ] SSL está ativo (HTTPS)
- [ ] Mobile responsivo funciona bem

### 🐛 Solução de Problemas no Deploy

**Erro: "Failed to fetch"**
- Verifique se o Supabase está configurado corretamente
- Confirme que as URLs estão atualizadas no Supabase

**Erro: "Provider is not enabled"**
- Configure o Google OAuth no Supabase (ver seção de autenticação)
- Adicione as URLs de produção no Google Cloud Console

**Imagens não carregam**
- Verifique se o Unsplash está acessível
- Confirme que não há bloqueio de CORS

**Build falha**
- Execute `npm run build` localmente para identificar erros
- Verifique versões do Node (use 18+)
- Limpe cache: `rm -rf node_modules package-lock.json && npm install`

### Configurar URLs de Produção

Após o deploy, você precisa:

1. Adicionar a URL de produção nas configurações do Supabase:
   - **Authentication > URL Configuration**
   - Site URL: `https://seu-dominio.com`
   - Redirect URLs: `https://seu-dominio.com/**`

2. Adicionar a URL no Google Cloud Console:
   - **Credentials > OAuth 2.0 Client IDs**
   - Authorized redirect URIs: `https://seu-dominio.com/auth/callback`

## 🔧 Tecnologias Utilizadas

### Frontend
- React 18
- TypeScript
- Tailwind CSS v4
- Shadcn/UI
- Lucide Icons
- Recharts
- React Hook Form
- Zod (validação)

### Backend
- Supabase
- Deno
- Hono (Web Framework)
- PostgreSQL

### Autenticação
- Supabase Auth
- Google OAuth 2.0

## 📚 Modelos YOLO

O sistema suporta três variações do YOLOv8:

### YOLOv8n (Nano)
- **Velocidade**: Muito Rápido (~100 FPS)
- **Precisão**: Boa (~70-75%)
- **Uso**: Ideal para hardware limitado

### YOLOv8s (Small)
- **Velocidade**: Rápido (~60-80 FPS)
- **Precisão**: Muito Boa (~75-80%)
- **Uso**: Balanceado, recomendado

### YOLOv8m (Medium)
- **Velocidade**: Moderado (~40-50 FPS)
- **Precisão**: Excelente (~80-85%)
- **Uso**: Melhor precisão, hardware robusto

## 🐛 Solução de Problemas

### Erro: "Provider is not enabled"
- Certifique-se de ter configurado o Google OAuth no Supabase
- Verifique se as URLs de redirecionamento estão corretas

### Erro: "Failed to fetch"
- Verifique se o backend Supabase está rodando
- Confirme as credenciais em `utils/supabase/info.tsx`

### Câmeras não aparecem
- Verifique se o sistema está iniciado (botão "Iniciar Sistema")
- Confirme que as imagens do Unsplash estão carregando

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor:

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'Adiciona MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto é licenciado sob a licença MIT - veja o arquivo LICENSE para detalhes.

## 👥 Equipe

Desenvolvido para otimizar o processo de reciclagem e tornar o mundo mais sustentável através da tecnologia.

## 📞 Suporte

Para dúvidas ou suporte, abra uma issue no GitHub ou entre em contato através do email do projeto.

---

**EcoVision** - Transformando reciclagem com Inteligência Artificial 🌱♻️
