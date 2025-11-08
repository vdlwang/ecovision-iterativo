# 🗄️ Migrações do Banco de Dados EcoVision

Este diretório contém as migrações SQL para o banco de dados PostgreSQL do EcoVision.

## 📋 Migrações Disponíveis

### `001_create_ecovision_tables.sql`
**Data:** 2025-11-08  
**Versão:** 1.0.0

**Cria as seguintes tabelas:**
1. ✅ `profiles` - Perfil do usuário com dados adicionais
2. ✅ `user_sessions` - Rastreamento de sessões
3. ✅ `inferences` - Registro de cada detecção IA
4. ✅ `system_config` - Configurações do sistema
5. ✅ `statistics` - Estatísticas agregadas diárias
6. ✅ `system_logs` - Logs e auditoria

**Inclui também:**
- 🔐 Row Level Security (RLS) em todas as tabelas
- 📊 3 Views pré-definidas
- ⚡ 4 Triggers automáticos
- 🔑 Índices de performance
- ✅ Constraints e validações

## 🚀 Como Executar as Migrações

### Opção 1: Supabase Dashboard (Recomendado)

1. Acesse seu projeto no [Supabase Dashboard](https://supabase.com/dashboard)
2. Vá em **SQL Editor** no menu lateral
3. Clique em **New Query**
4. Copie todo o conteúdo de `001_create_ecovision_tables.sql`
5. Cole no editor e clique em **Run**
6. Aguarde a mensagem de sucesso: ✅ "Migração concluída com sucesso!"

### Opção 2: Supabase CLI

```bash
# Certifique-se de que o Supabase CLI está instalado
npm install -g supabase

# Faça login (se ainda não estiver logado)
supabase login

# Link com seu projeto
supabase link --project-ref seu-project-id

# Execute a migração
supabase db push
```

### Opção 3: Executar SQL Diretamente

```bash
# Via psql (se tiver acesso direto ao PostgreSQL)
psql "postgresql://postgres:senha@db.seu-projeto.supabase.co:5432/postgres" \
  -f supabase/migrations/001_create_ecovision_tables.sql
```

## ✅ Verificação Pós-Migração

Após executar a migração, verifique se tudo está correto:

### 1. Verificar Tabelas Criadas

Execute no SQL Editor:

```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN ('profiles', 'user_sessions', 'inferences', 
                     'system_config', 'statistics', 'system_logs');
```

**Resultado esperado:** 6 linhas (uma para cada tabela)

### 2. Verificar Triggers

```sql
SELECT trigger_name, event_object_table 
FROM information_schema.triggers 
WHERE trigger_schema = 'public';
```

**Resultado esperado:** Pelo menos 4 triggers

### 3. Verificar Views

```sql
SELECT table_name 
FROM information_schema.views 
WHERE table_schema = 'public';
```

**Resultado esperado:** 3 views (v_user_dashboard, v_session_summary, v_material_stats)

### 4. Verificar RLS

```sql
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' 
  AND rowsecurity = true;
```

**Resultado esperado:** 6 tabelas com RLS habilitado

## 🔧 Estrutura das Tabelas

### `profiles`
- **Propósito:** Dados adicionais do perfil do usuário
- **Relacionamento:** 1:1 com `auth.users`
- **RLS:** ✅ Habilitado (usuário acessa apenas próprio perfil)

### `user_sessions`
- **Propósito:** Rastreamento de sessões
- **Relacionamento:** N:1 com `auth.users`
- **Triggers:** Calcula duração automaticamente, incrementa contador

### `inferences`
- **Propósito:** Registro de cada detecção IA
- **Relacionamento:** N:1 com `user_sessions` e `auth.users`
- **Constraints:** Confiança 0-100, material válido, cancela 1-3

### `system_config`
- **Propósito:** Configurações por usuário
- **Relacionamento:** N:1 com `auth.users`
- **Constraint Único:** Apenas 1 config ativa por usuário

### `statistics`
- **Propósito:** Agregação diária de dados
- **Relacionamento:** N:1 com `auth.users`
- **Constraint Único:** 1 linha por usuário por dia

### `system_logs`
- **Propósito:** Logs e auditoria
- **Relacionamento:** N:1 com `user_sessions` e `auth.users`
- **Níveis:** DEBUG, INFO, WARNING, ERROR, CRITICAL

## 📊 Diagrama do Banco

Para visualizar o diagrama completo do banco de dados, consulte:
- **Arquivo:** `/diagrams/database-diagram.puml`
- **Documentação:** `/diagrams/INDEX.md`

## 🔄 Rollback (Reverter Migração)

Se precisar reverter a migração, execute:

```sql
-- ATENÇÃO: Isso irá DELETAR todas as tabelas e dados!

DROP TRIGGER IF EXISTS trigger_create_profile ON auth.users CASCADE;
DROP TRIGGER IF EXISTS trigger_increment_counter ON public.user_sessions CASCADE;
DROP TRIGGER IF EXISTS trigger_calculate_duration ON public.user_sessions CASCADE;
DROP TRIGGER IF EXISTS update_statistics_updated_at ON public.statistics CASCADE;
DROP TRIGGER IF EXISTS update_config_updated_at ON public.system_config CASCADE;
DROP TRIGGER IF EXISTS update_profiles_updated_at ON public.profiles CASCADE;

DROP VIEW IF EXISTS public.v_material_stats CASCADE;
DROP VIEW IF EXISTS public.v_session_summary CASCADE;
DROP VIEW IF EXISTS public.v_user_dashboard CASCADE;

DROP TABLE IF EXISTS public.system_logs CASCADE;
DROP TABLE IF EXISTS public.statistics CASCADE;
DROP TABLE IF EXISTS public.system_config CASCADE;
DROP TABLE IF EXISTS public.inferences CASCADE;
DROP TABLE IF EXISTS public.user_sessions CASCADE;
DROP TABLE IF EXISTS public.profiles CASCADE;

DROP FUNCTION IF EXISTS create_profile_for_user() CASCADE;
DROP FUNCTION IF EXISTS increment_session_counter() CASCADE;
DROP FUNCTION IF EXISTS calculate_session_duration() CASCADE;
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;
```

## 🐛 Troubleshooting

### Erro: "relation already exists"
**Causa:** Tabela já foi criada anteriormente  
**Solução:** As queries usam `IF NOT EXISTS`, então não há problema. Ou execute o rollback primeiro.

### Erro: "permission denied"
**Causa:** Usuário não tem permissões suficientes  
**Solução:** Use a conexão com o usuário `postgres` (admin)

### Erro: "auth.users does not exist"
**Causa:** Supabase Auth não está habilitado  
**Solução:** Verifique se o projeto Supabase está configurado corretamente

### Erro: "trigger already exists"
**Causa:** Triggers já foram criados  
**Solução:** Execute `DROP TRIGGER ... CASCADE` antes de recriar

## 📝 Próximas Migrações

Futuras migrações devem seguir o padrão:
- `002_add_feature_X.sql`
- `003_alter_table_Y.sql`
- etc.

Sempre inclua:
- Comentários descrevendo a mudança
- Verificações de segurança (`IF EXISTS`, `IF NOT EXISTS`)
- Rollback opcional no final (comentado)

## 🔗 Referências

- [Supabase Migrations](https://supabase.com/docs/guides/cli/local-development#database-migrations)
- [PostgreSQL Triggers](https://www.postgresql.org/docs/current/sql-createtrigger.html)
- [Row Level Security](https://supabase.com/docs/guides/auth/row-level-security)
- [Diagrama ER do EcoVision](/diagrams/database-diagram.puml)

---

**EcoVision** - Sistema de Reciclagem Inteligente 🌱♻️
