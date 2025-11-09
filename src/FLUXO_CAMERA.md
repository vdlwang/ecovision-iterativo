# 📹 Fluxo Completo da Câmera - EcoVision

## 🎯 Passo a Passo Visual

### Passo 1: Login
```
┌─────────────────────────────────┐
│     [Logo EcoVision]            │
│                                 │
│  Email: _________________       │
│  Senha: _________________       │
│                                 │
│     [ Entrar com Google ]       │
│     [ Entrar ]                  │
│                                 │
└─────────────────────────────────┘
```
**👆 Faça login (Google OAuth ou Modo Demo)**

---

### Passo 2: Permissão Automática
```
┌─────────────────────────────────┐
│  exemplo.com quer usar:         │
│                                 │
│  📹 Sua câmera                  │
│                                 │
│  [ Bloquear ]  [ Permitir ]     │
└─────────────────────────────────┘
```
**👆 Navegador solicita permissão AUTOMATICAMENTE**
**✅ Clique em "Permitir"**

---

### Passo 3: Interface Pronta
```
┌─────────────────────────────────────────┐
│  MONITOR DO SISTEMA                     │
├─────────────────────┬───────────────────┤
│  ESTEIRA ROLANTE    │  CÂMERA PRINCIPAL │
│                     │                   │
│  [Parada]           │   🎥              │
│                     │                   │
│  [ Iniciar ]        │  Câmera Pronta    │
│                     │                   │
│  [C1] [C2] [C3]     │  [Iniciar Sistema]│
│                     │                   │
└─────────────────────┴───────────────────┘
```
**👆 Você verá 2 botões "Iniciar":**
- **Botão esquerdo (Esteira)**: Liga a animação da esteira
- **Botão direito (Câmera)**: Ativa a câmera e detecções ✅

---

### Passo 4: Sistema Rodando
```
┌─────────────────────────────────────────┐
│  MONITOR DO SISTEMA                     │
├─────────────────────┬───────────────────┤
│  ESTEIRA ROLANTE    │  CÂMERA PRINCIPAL │
│                     │                   │
│  [EM MOVIMENTO] ⚡  │  [AO VIVO] 📹     │
│                     │                   │
│  >>>>>>>>>>>>>>     │  ┌──────────────┐ │
│                     │  │   📦 VÍDEO   │ │
│  [ Parar ]          │  │   AO VIVO    │ │
│                     │  │   +BBOX      │ │
│  [C1]🟢[C2][C3]     │  └──────────────┘ │
│                     │  [ Parar ]        │
└─────────────────────┴───────────────────┘
```
**✅ Sistema detectando em tempo real!**

---

## ⚡ Resumo Rápido

| Ação | O Que Fazer |
|------|-------------|
| 1️⃣ Login | Entre com Google ou Modo Demo |
| 2️⃣ Popup | Clique "Permitir" no navegador |
| 3️⃣ Câmera | Clique "Iniciar Sistema" no feed da câmera (direita) |
| 4️⃣ Esteira | (Opcional) Clique "Iniciar" na esteira (esquerda) |
| ✅ Pronto! | Sistema detectando materiais! |

---

## 🐛 Problemas Comuns

### "Câmera Pronta para Iniciar" mas sem botão
**❌ Problema antigo** (já corrigido!)

Se você ver essa mensagem SEM botão:
1. Atualize a página (F5)
2. Faça login novamente
3. Agora verá o botão "Iniciar Sistema"

### Permissão de câmera bloqueada
Se você bloqueou por engano:

**Chrome/Edge:**
1. Clique no cadeado 🔒 ao lado da URL
2. Configurações do site → Câmera → Permitir
3. Recarregue a página (F5)

**Firefox:**
1. Clique no ícone da câmera 🎥 na barra de endereço
2. Limpar permissões
3. Recarregue a página (F5)

### Câmera não funciona em HTTP
⚠️ **Solução:**
- Use `http://localhost:5000` (funciona!)
- Ou use HTTPS em produção
- Não use `http://192.168.x.x` (bloqueado pelos navegadores)

---

## 💡 Dicas

✅ **Bom para saber:**
- A solicitação de permissão é automática (não precisa clicar nada antes)
- Você pode pausar/retomar a detecção a qualquer momento
- A esteira é só visual - não precisa estar rodando para detectar
- As detecções aparecem em "Detecções Recentes" abaixo do monitor

🎯 **Ordem recomendada:**
1. Login
2. Permitir câmera
3. Iniciar câmera
4. Iniciar esteira (opcional, só visual)
5. Ajustar confiança mínima (aba "Especificações de Modelo")
6. Configurar cancelas (aba "Configuração de Cancelas")

---

## 📖 Mais Informações

- **Guia de instalação completo**: [COMO_EXECUTAR.md](COMO_EXECUTAR.md)
- **Início rápido**: [START.md](START.md)
- **Problemas com câmera**: [CAMERA_TROUBLESHOOTING.md](CAMERA_TROUBLESHOOTING.md)
- **Documentação principal**: [README.md](README.md)
