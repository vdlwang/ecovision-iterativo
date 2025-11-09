# 🎯 EcoVision - Modo Demo

Guia completo sobre o Modo Demo do EcoVision e como configurar autenticação real.

---

## ✅ O Que Foi Corrigido

### Problema Original
```
[AUTH] Nenhuma sessão ativa encontrada.
AuthApiError: invalid claim: missing sub claim
```

**Causa:** Google OAuth não estava configurado no Supabase, impedindo login de usuários reais.

### Solução Implementada

Criamos um **Modo Demo** totalmente funcional que permite testar o sistema sem necessidade de configurar autenticação:

1. ✅ **Token Demo Especial** - Backend aceita token `DEMO_MODE_TOKEN_ecovision_2024`
2. ✅ **Usuário Demo** - ID fixo `demo-user-ecovision-2024`
3. ✅ **Indicadores Visuais** - Banner amarelo e badge no perfil
4. ✅ **Instruções na Tela de Login** - Como configurar Google OAuth
5. ✅ **Funcionalidade Completa** - Todas as features funcionam em demo

---

## 🚀 Como Usar o Modo Demo

### 1. Iniciar Aplicação

```bash
# Terminal 1: Iniciar o servidor de inferência Python
python inference_server.py

# Terminal 2: Iniciar a aplicação web (via Figma Make)
# A aplicação já inicia automaticamente
```

### 2. Fazer Login em Modo Demo

1. Abra a aplicação no navegador
2. Você verá a tela de login com duas opções:
   - **Entrar com Google** (requer configuração)
   - **Entrar em Modo Demo** ← Use esta!
3. Clique em **"Entrar em Modo Demo"**
4. Pronto! Você está dentro do sistema

### 3. Identificar Modo Demo

Quando em modo demo, você verá:

**Banner no topo:**
```
⚗️ Modo Demonstração Ativo
Você está usando o EcoVision em modo demo. Os dados não serão salvos 
permanentemente. Para salvar suas configurações e dados, configure o 
login com Google no Supabase.
```

**Badge no perfil:**
- Badge amarelo com ícone de tubo de ensaio: "🧪 Modo Demo"

**Logs no console:**
```
[AUTH] Entrando em Modo Demo
[DEMO] Usando usuário demo
```

---

## 🔐 Configurar Autenticação Real (Google OAuth)

Se você quiser que usuários reais façam login e seus dados sejam salvos:

### Passo 1: Criar Projeto no Google Cloud

1. Acesse: https://console.cloud.google.com
2. Crie um novo projeto ou selecione um existente
3. Vá em **APIs & Services** → **Credentials**
4. Clique em **+ Create Credentials** → **OAuth 2.0 Client ID**

### Passo 2: Configurar OAuth Consent Screen

1. Clique em **Configure Consent Screen**
2. Escolha **External** (para testes) ou **Internal** (para organização)
3. Preencha:
   - **App name:** EcoVision
   - **User support email:** seu email
   - **Developer contact:** seu email
4. Salve e continue

### Passo 3: Criar OAuth Client ID

1. Volte para **Credentials** → **+ Create Credentials** → **OAuth 2.0 Client ID**
2. **Application type:** Web application
3. **Name:** EcoVision Web Client
4. **Authorized JavaScript origins:**
   ```
   http://localhost:5173
   https://SEU_PROJECT_ID.supabase.co
   ```
5. **Authorized redirect URIs:**
   ```
   http://localhost:5173/auth/callback
   https://SEU_PROJECT_ID.supabase.co/auth/v1/callback
   ```
6. Clique em **Create**
7. **IMPORTANTE:** Copie o **Client ID** e **Client Secret**

### Passo 4: Configurar no Supabase

1. Acesse o Dashboard do Supabase: https://supabase.com/dashboard
2. Selecione seu projeto
3. Vá em **Authentication** → **Providers**
4. Encontre **Google** na lista
5. Clique para expandir
6. **Ative** o toggle "Enable Sign in with Google"
7. Cole:
   - **Client ID:** (do Google Cloud)
   - **Client Secret:** (do Google Cloud)
8. Clique em **Save**

### Passo 5: Configurar Redirect URLs

1. Ainda em **Authentication**, vá em **URL Configuration**
2. Adicione as seguintes URLs em **Redirect URLs:**
   ```
   http://localhost:5173
   http://localhost:5173/auth/callback
   https://SEU_DOMINIO.com (se tiver)
   ```
3. Em **Site URL**, coloque:
   ```
   http://localhost:5173
   ```

### Passo 6: Testar Login

1. Recarregue a aplicação
2. Clique em **"Entrar com Google"**
3. Selecione sua conta Google
4. Autorize o aplicativo
5. Você será redirecionado de volta para a aplicação

✅ **Pronto!** Agora você tem autenticação real funcionando.

---

## 🔄 Diferenças: Demo vs Real

| Recurso | Modo Demo | Autenticação Real |
|---------|-----------|-------------------|
| Login | Clique no botão "Modo Demo" | Login com Google OAuth |
| Dados Salvos | ❌ Não são salvos no banco | ✅ Salvos no PostgreSQL |
| Sessões | ⚠️ Perdidas ao recarregar | ✅ Persistem entre sessões |
| Configurações | ⚠️ Temporárias | ✅ Salvas permanentemente |
| Estatísticas | ⚠️ Zeradas a cada login | ✅ Acumuladas ao longo do tempo |
| Histórico | ❌ Não disponível | ✅ Completo e detalhado |
| Múltiplos Usuários | ❌ Todos compartilham mesmo "demo-user" | ✅ Cada usuário tem seus próprios dados |
| Token | Token fixo (não expira) | JWT que expira em 1h (renovável) |

---

## 🐛 Troubleshooting

### Erro: "Não autorizado" mesmo em modo demo

**Sintoma:**
```
[INFERENCE] Falha na autenticação do usuário
Error 401: Token de autenticação inválido ou expirado
```

**Solução:**
1. Verifique os logs do backend
2. Procure por `[DEMO] Usando usuário demo`
3. Se não aparecer, o token não está sendo enviado corretamente

**Verificar no console do navegador (F12):**
```javascript
// Verificar token atual
console.log('Token:', localStorage.getItem('supabase.auth.token'));

// Deve mostrar: DEMO_MODE_TOKEN_ecovision_2024
```

**Se o token estiver incorreto:**
1. Faça logout
2. Recarregue a página (Ctrl+Shift+R)
3. Entre em modo demo novamente

### Erro: Google OAuth não funciona

**Sintoma:**
```
Erro ao fazer login com Google. Por favor, configure o Google OAuth 
no Supabase ou use o Modo Demo.
```

**Causas possíveis:**

1. **Client ID/Secret incorretos**
   - Verifique se copiou corretamente do Google Cloud
   - Certifique-se de não ter espaços no início/fim

2. **Redirect URLs não configuradas**
   - Adicione todas as URLs no Google Cloud E no Supabase
   - URLs devem corresponder exatamente (incluindo http/https)

3. **Projeto Google Cloud não configurado**
   - Verifique se criou OAuth Consent Screen
   - Verifique se o projeto está ativo

**Solução temporária:**
- Use o Modo Demo enquanto configura o OAuth!

### Banner de demo não aparece

**Causa:** Estado `isDemoMode` não está sendo passado corretamente.

**Solução:**
1. Verifique no console se aparece: `[AUTH] Entrando em Modo Demo`
2. Recarregue a página
3. Faça logout e entre em demo novamente

---

## 📊 Dados em Modo Demo

### O Que É Salvo (Temporariamente)

Em modo demo, os dados são mantidos **apenas durante a sessão atual**:

✅ **Configurações de cancelas** (memória do navegador)
✅ **Modelo e confiança mínima** (memória do navegador)
✅ **Detecções em tempo real** (enquanto sistema está rodando)

### O Que NÃO É Salvo

❌ **Banco de dados PostgreSQL** - Não grava nada
❌ **Estatísticas históricas** - Reset a cada login
❌ **Sessões anteriores** - Não há histórico
❌ **Configurações personalizadas** - Perdidas ao recarregar

### Como Testar Salvamento Real

Para testar se os dados estão sendo salvos no banco:

1. Configure autenticação real (Google OAuth)
2. Faça login com sua conta Google
3. Configure uma cancela para "papel"
4. Faça logout
5. Faça login novamente
6. ✅ **A configuração deve permanecer "papel"**

Se não permanecer, verifique:
- Endpoint `/config` (POST) está salvando no banco?
- RLS (Row Level Security) está configurado?
- Token está sendo enviado corretamente?

---

## 🔒 Segurança

### Token Demo É Seguro?

⚠️ **Em produção, NÃO!**

O token demo `DEMO_MODE_TOKEN_ecovision_2024` é:
- ✅ **Seguro para desenvolvimento local**
- ✅ **Seguro para demonstrações**
- ❌ **NÃO seguro para produção**
- ❌ **NÃO deve estar em ambiente público**

### Como Desabilitar Modo Demo em Produção

Em `/supabase/functions/server/index.tsx`, **comente** ou **remova** este bloco:

```typescript
// MODO DEMO: Token especial para desenvolvimento/testes
if (token === 'DEMO_MODE_TOKEN_ecovision_2024') {
  console.log('[DEMO] Usando usuário demo');
  return {
    id: 'demo-user-ecovision-2024',
    email: 'demo@ecovision.com',
    aud: 'authenticated',
    role: 'authenticated'
  };
}
```

Ou adicione verificação de ambiente:

```typescript
// Apenas permitir demo em desenvolvimento
const isDevelopment = Deno.env.get('ENVIRONMENT') === 'development';

if (isDevelopment && token === 'DEMO_MODE_TOKEN_ecovision_2024') {
  // ... resto do código demo
}
```

---

## 🎓 Boas Práticas

### Para Desenvolvimento

✅ **Use Modo Demo** para:
- Testes rápidos
- Desenvolvimento de novas features
- Demonstrações para clientes
- Prototipagem de UI/UX

❌ **NÃO use Modo Demo** para:
- Testar salvamento de dados
- Testar autenticação
- Performance com múltiplos usuários
- Dados de produção

### Para Produção

✅ **Configure Google OAuth** antes de publicar
✅ **Desabilite modo demo** em produção
✅ **Configure RLS** corretamente
✅ **Teste fluxo completo** de login/logout
✅ **Configure backup** do banco de dados

---

## 📞 Suporte

Se você está tendo problemas:

1. **Verifique os logs:**
   - Console do navegador (F12 → Console)
   - Logs do backend (Supabase Dashboard → Edge Functions → Logs)

2. **Teste em ordem:**
   - ✅ Modo Demo funciona?
   - ✅ Google OAuth configurado?
   - ✅ Redirect URLs corretas?
   - ✅ Token está sendo enviado?

3. **Documentação útil:**
   - `AUTH_TROUBLESHOOTING.md` - Diagnóstico de autenticação
   - `QUICKSTART.md` - Setup inicial
   - `WEBCAM_INFERENCE_SETUP.md` - Configuração de webcam

---

## 🎉 Resumo

O Modo Demo permite você:
- ✅ Testar o sistema **imediatamente**
- ✅ Sem necessidade de configurar OAuth
- ✅ Todas as features funcionam
- ✅ Perfeito para desenvolvimento e demos

Quando estiver pronto para produção:
- 🔐 Configure Google OAuth
- 💾 Dados serão salvos permanentemente
- 👥 Suporte para múltiplos usuários
- 📊 Estatísticas e histórico completos

**Aproveite o EcoVision! 🌱♻️**

---

**Última atualização:** 09 de Novembro de 2025
