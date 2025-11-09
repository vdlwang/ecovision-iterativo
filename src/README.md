# 🌿 EcoVision - Sistema Inteligente de Reciclagem com IA

![Status](https://img.shields.io/badge/Status-Funcional-brightgreen?style=flat-square)
![React](https://img.shields.io/badge/React-TypeScript-blue?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.8+-yellow?style=flat-square)
![YOLO](https://img.shields.io/badge/YOLOv8-Ultralytics-purple?style=flat-square)

**Sistema de controle para esteira de reciclagem com detecção automática de materiais usando visão computacional e IA**

---

## 📋 O Que é o EcoVision?

Sistema completo para centros de reciclagem que:
- 📹 Captura imagens da webcam em tempo real
- 🤖 Detecta materiais (papel, metal, plástico, vidro) com IA YOLO
- 🚪 Aciona cancelas automaticamente para separação
- 📊 Monitora estatísticas e performance
- 🔐 Autenticação com Google OAuth ou modo demo

---

## 🎯 Como Funciona

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Webcam   │───▶│ IA YOLO  │───▶│ Cancelas │───▶│Dashboard │
│ Captura  │    │ Detecta  │    │ Separam  │    │Estatístic│
└──────────┘    └──────────┘    └──────────┘    └──────────┘
```

1. Câmera captura frames da esteira
2. YOLO detecta e classifica materiais
3. Sistema aciona a cancela correta
4. Material é separado automaticamente
5. Dashboard registra todas as detecções

---

## 🚀 Início Rápido

### Pré-requisitos
- Node.js 18+ 
- Python 3.8+ (opcional, para inferência avançada)
- Webcam conectada
- Navegador moderno (Chrome/Edge recomendado)

### Instalação

```bash
# 1. Clone o repositório
git clone <seu-repo>
cd ecovision

# 2. Instale dependências Python (opcional)
pip install -r requirements.txt

# 3. Execute o sistema
./run_dev.sh        # Linux/Mac
# ou
run_dev.bat         # Windows

# 4. Acesse http://localhost:5000
```

### Primeiro Uso

1. **Login**: Clique em "Modo Demo" (ou configure Google OAuth)
2. **Permita a câmera** quando solicitado pelo navegador
3. **Configure as cancelas** na aba "Configuração"
4. **Inicie o sistema** na aba "Monitor"
5. **Veja as detecções** em tempo real!

---

## 🏗️ Arquitetura do Sistema

### Stack Tecnológico

**Frontend:**
- React + TypeScript
- Tailwind CSS
- Shadcn/ui components
- ONNX Runtime Web (inferência no navegador)

**Backend:**
- Supabase (Database + Auth + Edge Functions)
- Deno (servidor backend)
- PostgreSQL (via Supabase)

**IA/ML:**
- YOLOv8 (Ultralytics)
- ONNX Runtime
- Python FastAPI (opcional, para inferência avançada)

### Estrutura de Pastas

```
ecovision/
├── App.tsx                    # Aplicação React principal
├── components/                # Componentes React
│   ├── Login.tsx             # Autenticação
│   ├── MonitorPanel.tsx      # Painel de monitoramento
│   ├── CameraFeed.tsx        # Feed da câmera + IA
│   ├── GateConfiguration.tsx # Config de cancelas
│   ├── AccuracyControl.tsx   # Controle de modelo
│   ├── StatisticsPanel.tsx   # Dashboard
│   ├── UserProfile.tsx       # Perfil do usuário
│   └── Sidebar.tsx           # Menu lateral
├── utils/
│   ├── onnxInference.tsx     # Inferência ONNX no navegador
│   └── supabase/             # Cliente Supabase
├── supabase/
│   └── functions/server/     # Backend Deno
│       └── index.tsx         # Servidor API REST
├── models/                    # Modelos YOLO (.onnx)
├── inference_server.py        # Servidor Python (opcional)
└── convert_to_onnx.py        # Conversor YOLO → ONNX
```

---

## 🎮 Funcionalidades

### ✅ Completas e Funcionando

- [x] **Login/Auth**: Google OAuth + Modo Demo
- [x] **Captura de Vídeo**: Webcam em tempo real
- [x] **Detecção IA**: YOLO com 4 classes de materiais
- [x] **Bounding Boxes**: Desenha detecções na tela
- [x] **Cancelas**: 3 cancelas configuráveis
- [x] **Dashboard**: Estatísticas e gráficos
- [x] **Histórico**: Registro de todas as detecções
- [x] **Perfil**: Dados do usuário e sessões
- [x] **Responsivo**: Desktop e mobile

### 🎯 Modos de Inferência

O sistema suporta 3 modos (em ordem de prioridade):

1. **ONNX no Navegador** ⭐ (Recomendado)
   - Processamento local, super rápido
   - Privacidade total (nada sai do navegador)
   - Requer: arquivo `/models/yolov8n.onnx`

2. **Servidor Python** (Fallback)
   - Suporta GPU (CUDA)
   - Modelos .pt nativos do YOLO
   - Requer: `python inference_server.py` rodando

3. **Mock** (Desenvolvimento)
   - Detecções simuladas aleatórias
   - Sempre disponível
   - Apenas para testes

---

## ⚙️ Configuração

### 1. Modelos YOLO

**Opção A: ONNX (Recomendado)**
```bash
# Baixe modelo treinado YOLOv8
# Coloque em /models/yolov8n.onnx

# OU converta seu próprio modelo:
python convert_to_onnx.py --weights best.pt --output models/
```

**Opção B: Servidor Python**
```bash
# Coloque modelo .pt em /models/
# Execute servidor:
python inference_server.py
```

### 2. Google OAuth (Opcional)

Para login real com Google:

1. Acesse [Supabase Dashboard](https://supabase.com)
2. Navegue: Authentication → Providers → Google
3. Siga instruções para obter Client ID/Secret
4. Configure no Supabase

Sem OAuth: use **Modo Demo** (funciona 100%)

### 3. Configuração de Cancelas

No painel "Configuração":
- **Cancela 1**: Escolha qual material (papel, metal, plástico, vidro)
- **Cancela 2**: Escolha outro material
- **Cancela 3**: Escolha terceiro material
- **Confiança Mínima**: 50-95% (padrão: 85%)

---

## 🐛 Troubleshooting

### Problema: Câmera não inicia

**Solução:**
1. Verifique permissões do navegador (ícone 🔒 na barra de endereço)
2. Use Chrome/Edge (melhor compatibilidade)
3. Acesse via `http://localhost:5000` (não IP)
4. Feche outros apps usando a câmera (Zoom, Teams, etc.)

### Problema: Detecções não aparecem

**Solução:**
1. Verifique se há modelo em `/models/yolov8n.onnx`
2. Ou inicie servidor Python: `python inference_server.py`
3. Sistema funcionará em modo mock se ambos faltarem

### Problema: Erros 401 (JWT Inválido)

**Solução:**
- Se em **Modo Demo**: ignore (normal, estatísticas limitadas)
- Se com **OAuth**: faça logout/login novamente

### Problema: ONNX não carrega

**Solução:**
- Verifique conexão com internet (precisa baixar WASM do CDN)
- Sistema fará fallback automático para servidor/mock
- Funcionalidade não é afetada

---

## 📊 Banco de Dados

### Estrutura (PostgreSQL via Supabase)

```sql
-- Tabela KV Store (chave-valor genérica)
kv_store_ea835390 (
  key TEXT PRIMARY KEY,
  value JSONB,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
)

-- Armazena:
-- - Configurações do sistema
-- - Detecções
-- - Estatísticas de usuários
-- - Histórico de sessões
```

**Nota:** O sistema usa um KV store flexível. Não requer migrations ou DDL manual.

---

## 🔧 Desenvolvimento

### Scripts Úteis

```bash
# Desenvolvimento local
./run_dev.sh

# Converter modelo YOLO → ONNX
python convert_to_onnx.py --weights best.pt

# Servidor Python (inferência avançada)
python inference_server.py

# Testar setup
python test_setup.py
```

### Estrutura de Classes Backend

```typescript
// Padrão MVC com classes
ModeloIA          // Gerencia inferência
Cancela           // Controla cancelas
Esteira           // Controla esteira
Camera            // Gerencia câmera
Dashboard         // Estatísticas
Usuario           // Gerencia usuários
BancoDeDados      // Acesso ao KV store
```

---

## 📚 Tecnologias Utilizadas

| Categoria | Tecnologia | Uso |
|-----------|------------|-----|
| **Frontend** | React + TypeScript | Interface do usuário |
| **Estilização** | Tailwind CSS | Design responsivo |
| **Componentes** | Shadcn/ui | Componentes prontos |
| **Backend** | Supabase + Deno | Servidor e database |
| **IA** | YOLOv8 Ultralytics | Detecção de objetos |
| **Runtime IA** | ONNX Runtime Web | Inferência no navegador |
| **Auth** | Supabase Auth | Login social |
| **Database** | PostgreSQL | Armazenamento |
| **Charts** | Recharts | Gráficos e estatísticas |

---

## 🎨 Paleta de Cores

Sistema usa esquema de cores específico para materiais:

```css
Papel:    #163b6f (azul escuro)
Metal:    #196626 (verde escuro)
Plástico: #dc1f2e (vermelho)
Vidro:    #d2b91f (amarelo/dourado)

Sistema:  #034732 → #abf2ab (verde reciclagem)
```

---

## 🤝 Como Contribuir

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'Add: nova feature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

---

## 📄 Licença

Este projeto está sob licença MIT. Veja arquivo LICENSE para mais detalhes.

---

## 🆘 Suporte

### Problemas Comuns

Todos os erros conhecidos foram corrigidos na versão atual:
- ✅ Connection Refused → Resolvido
- ✅ ONNX WASM Loading → Resolvido com fallback
- ✅ JWT 401 Errors → Resolvido com detecção de modo demo
- ✅ Camera Permission → Mensagens melhoradas

### Logs e Debugging

O sistema usa console logging extensivo:
- `[AUTH]` - Autenticação
- `[CÂMERA]` - Operações de câmera
- `[ONNX]` - Inferência ONNX
- `[INFERÊNCIA]` - Detecções
- `[DASHBOARD]` - Estatísticas
- `[PERFIL]` - Perfil do usuário

Abra DevTools (F12) para ver logs detalhados.

---

## 📞 Contato

Dúvidas ou sugestões? Abra uma Issue no GitHub!

---

<div align="center">

**Desenvolvido com 💚 para um planeta mais sustentável**

🌿 EcoVision - Reciclagem Inteligente 🌿

</div>
