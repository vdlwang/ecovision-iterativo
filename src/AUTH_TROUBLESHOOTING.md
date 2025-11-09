# 🔐 EcoVision - Troubleshooting de Autenticação

Guia para diagnosticar e resolver problemas de autenticação no EcoVision.

## 🔍 Erro Atual

```
AuthApiError: invalid claim: missing sub claim
```

**Significado:** O token JWT enviado não possui a claim 'sub' (subject), necessária para identificar o usuário.

---

## ✅ Checklist de Diagnóstico

### 1. Verificar se o usuário está autenticado

**Console do navegador (F12):**
```javascript
// Verificar sessão
const { data: { session } } = await supabase.auth.getSession();
console.log('Sessão:', session);
console.log('Token:', session?.access_token);
console.log('User ID:', session?.user?.id);
```

**Resultado esperado:**
- `session` deve existir
- `access_token` deve ser uma string longa (JWT)
- `user.id` deve ser um UUID

**Se sessão for null:**
- Faça logout e login novamente
- Limpe cookies do navegador
- Tente em aba anônima

### 2. Testar autenticação no backend

**Via curl:**
```bash
# Substitua YOUR_TOKEN pelo token obtido acima
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://SEU_PROJECT_ID.supabase.co/functions/v1/make-server-ea835390/auth-test
```

**Resultado esperado:**
```json
{
  "success": true,
  "message": "Autenticação funcionando corretamente",
  "user": {
    "id": "abc123...",
    "email": "seu@email.com"
  }
}
```

**Se retornar erro 401:**
- Token inválido ou expirado
- Faça logout e login novamente

### 3. Verificar configuração do Supabase

**Via Dashboard Supabase:**

1. Acesse: https://supabase.com/dashboard/project/SEU_PROJECT_ID
2. Vá em **Authentication** > **Users**
3. Verifique se seu usuário aparece na lista
4. Vá em **Authentication** > **Providers**
5. Verifique se Google OAuth está habilitado

**Configurações necessárias:**
- ✅ Google OAuth habilitado
- ✅ Redirect URLs configuradas
- ✅ Row Level Security (RLS) habilitado nas tabelas

### 4. Verificar logs do backend

**Via Supabase Dashboard:**
```
Dashboard > Edge Functions > make-server-ea835390 > Logs
```

**Procure por:**
- `[AUTH] Erro ao obter usuário`
- `[INFERENCE] Falha na autenticação`
- `invalid claim: missing sub claim`

**Via CLI (se rodando localmente):**
```bash
supabase functions logs make-server-ea835390
```

### 5. Verificar logs do frontend

**Console do navegador (F12):**

Procure por:
- `[AUTH] Sessão obtida com sucesso`
- `[AUTH] Usuário conectado com sucesso`
- `[INFERÊNCIA] Token de usuário não disponível`

---

## 🔧 Soluções Comuns

### Solução 1: Fazer Logout e Login Novamente

O método mais simples e eficaz:

1. Clique no botão de perfil (canto superior direito)
2. Clique em **"Sair"**
3. Aguarde ser redirecionado para tela de login
4. Clique em **"Entrar com Google"**
5. Autorize novamente o aplicativo

**Por que funciona:**
- Gera novo token JWT válido
- Renova todas as claims do token
- Atualiza a sessão no Supabase

### Solução 2: Limpar Cache e Cookies

Se logout/login não resolver:

**Chrome:**
1. F12 > Application > Storage
2. Clique em "Clear site data"
3. Recarregue a página (Ctrl+Shift+R)

**Firefox:**
1. F12 > Storage
2. Clique direito em cada item e "Delete All"
3. Recarregue a página (Ctrl+Shift+R)

### Solução 3: Verificar CORS

Se o erro persistir, pode ser problema de CORS:

**Editar `/supabase/functions/server/index.tsx`:**

Verifique se tem:
```typescript
app.use('*', cors({
  origin: '*',
  credentials: true
}));
```

**Verificar no frontend:**
```typescript
// Deve incluir Authorization header
headers: {
  'Content-Type': 'application/json',
  'Authorization': `Bearer ${userToken}`
}
```

### Solução 4: Renovar Token Automaticamente

**Adicionar no App.tsx:**

```typescript
useEffect(() => {
  // Renovar token a cada 50 minutos (tokens expiram em 1h)
  const interval = setInterval(async () => {
    const { data, error } = await supabase.auth.refreshSession();
    if (data.session) {
      setUserToken(data.session.access_token);
      console.log('[AUTH] Token renovado automaticamente');
    } else {
      console.error('[AUTH] Falha ao renovar token:', error);
    }
  }, 50 * 60 * 1000); // 50 minutos
  
  return () => clearInterval(interval);
}, []);
```

### Solução 5: Usar Variável de Ambiente Correta

**Verificar `/utils/supabase/info.tsx`:**

```typescript
export const projectId = 'SEU_PROJECT_ID'; // Correto
export const publicAnonKey = 'eyJhbGc...';  // Deve começar com eyJ
```

**NO FRONTEND, use APENAS publicAnonKey para criar o cliente:**
```typescript
const supabase = createClient(
  `https://${projectId}.supabase.co`,
  publicAnonKey  // ✅ Correto
  // NÃO use SUPABASE_SERVICE_ROLE_KEY aqui! ❌
);
```

---

## 🐛 Debug Avançado

### Inspecionar Token JWT

**Via jwt.io:**

1. Acesse https://jwt.io
2. Cole seu token no campo "Encoded"
3. Verifique a seção "Payload"

**Claims necessárias:**
```json
{
  "sub": "abc123...",        // ✅ DEVE EXISTIR (user ID)
  "email": "seu@email.com",
  "role": "authenticated",
  "aud": "authenticated",
  "exp": 1699999999,         // Timestamp de expiração
  "iat": 1699996399          // Timestamp de criação
}
```

**Se 'sub' estiver ausente:**
- Token corrompido ou inválido
- Faça logout e login novamente

**Se 'exp' estiver no passado:**
- Token expirado
- Faça logout e login novamente
- Ou use `supabase.auth.refreshSession()`

### Testar Backend Diretamente

**Script de teste (test_auth.js):**

```javascript
const projectId = 'SEU_PROJECT_ID';
const token = 'SEU_TOKEN_AQUI';

fetch(`https://${projectId}.supabase.co/functions/v1/make-server-ea835390/auth-test`, {
  headers: {
    'Authorization': `Bearer ${token}`
  }
})
.then(r => r.json())
.then(data => console.log('Resultado:', data))
.catch(err => console.error('Erro:', err));
```

**Executar:**
```bash
node test_auth.js
```

### Verificar Row Level Security (RLS)

Pode ser que as políticas RLS estejam bloqueando acesso:

**SQL Editor no Supabase:**

```sql
-- Verificar políticas na tabela inferences
SELECT * FROM pg_policies WHERE tablename = 'inferences';

-- Temporariamente desabilitar RLS (APENAS PARA TESTE!)
ALTER TABLE inferences DISABLE ROW LEVEL SECURITY;

-- Testar se funciona agora...

-- IMPORTANTE: Reabilitar depois!
ALTER TABLE inferences ENABLE ROW LEVEL SECURITY;
```

---

## 📋 Checklist Final

Antes de desistir, verifique:

- [ ] Fiz logout e login novamente
- [ ] Token existe no localStorage/sessionStorage
- [ ] Token tem claim 'sub' (verificado no jwt.io)
- [ ] Token não está expirado
- [ ] Backend retorna 200 no endpoint `/auth-test`
- [ ] Google OAuth está habilitado no Supabase
- [ ] Redirect URLs estão configuradas corretamente
- [ ] CORS está configurado no backend
- [ ] RLS não está bloqueando acesso
- [ ] Variáveis de ambiente estão corretas

---

## 🆘 Ainda com Problema?

### Opção 1: Modo Demo (Temporário)

Se precisar testar urgentemente:

```typescript
// Em App.tsx, adicionar botão de demo
const handleDemoMode = () => {
  setIsDemoMode(true);
  setUser({ 
    id: 'demo-user',
    email: 'demo@ecovision.com' 
  });
  setUserToken('demo-token'); // ⚠️ Não funcionará com backend real
};
```

**⚠️ AVISO:** Modo demo não salva dados no banco!

### Opção 2: Desabilitar Autenticação Temporariamente

**APENAS PARA DESENVOLVIMENTO LOCAL:**

Em `/supabase/functions/server/index.tsx`:

```typescript
async function getUserFromToken(authHeader: string | null) {
  // TEMPORÁRIO: Pular validação
  console.warn('⚠️ AUTENTICAÇÃO DESABILITADA - MODO DEBUG');
  return {
    id: 'debug-user-123',
    email: 'debug@localhost'
  };
}
```

**⚠️ NUNCA faça isso em produção!**

### Opção 3: Criar Usuário Manualmente

Via SQL Editor:

```sql
-- Criar usuário de teste
INSERT INTO auth.users (
  id,
  email,
  encrypted_password,
  email_confirmed_at,
  created_at,
  updated_at
) VALUES (
  gen_random_uuid(),
  'teste@ecovision.com',
  crypt('senha123', gen_salt('bf')),
  NOW(),
  NOW(),
  NOW()
);
```

Depois faça login com: `teste@ecovision.com` / `senha123`

---

## 📞 Suporte

Se nenhuma solução funcionou:

1. **Colete logs:**
   - Console do navegador (F12 > Console)
   - Logs do Edge Function (Supabase Dashboard)
   - Network tab (F12 > Network)

2. **Informações necessárias:**
   - Mensagem de erro completa
   - Token JWT (primeiros/últimos 20 caracteres)
   - Project ID do Supabase
   - Passos para reproduzir o erro

3. **Abra issue no GitHub:**
   - Inclua todas as informações acima
   - Não compartilhe tokens completos ou service role keys!

---

**Última atualização:** 09 de Novembro de 2025
