# 🗄️ Migrações do Banco de Dados EcoVision

Este diretório contém as migrações SQL para o banco de dados PostgreSQL do EcoVision.

## 📋 Migração Disponível

### `001_create_ecovision_tables.sql`

**Cria as seguintes tabelas:**
1. ✅ `profiles` - Perfil do usuário
2. ✅ `user_sessions` - Rastreamento de sessões
3. ✅ `inferences` - Registro de detecções IA
4. ✅ `system_config` - Configurações do sistema
5. ✅ `statistics` - Estatísticas agregadas
6. ✅ `system_logs` - Logs e auditoria

**Inclui:**
- 🔐 Row Level Security (RLS)
- 📊 3 Views pré-definidas
- ⚡ 4 Triggers automáticos
- 🔑 Índices de performance

## 🚀 Como Executar

### Opção 1: Supabase Dashboard (Recomendado)

1. Acesse [Supabase Dashboard](https://supabase.com/dashboard)
2. SQL Editor → New Query
3. Copie o conteúdo de `001_create_ecovision_tables.sql`
4. Cole e clique em **Run**

### Opção 2: Supabase CLI

```bash
supabase login
supabase link --project-ref seu-project-id
supabase db push
```

## ✅ Verificação

Execute no SQL Editor:

```sql
-- Verificar tabelas criadas
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN ('profiles', 'user_sessions', 'inferences', 
                     'system_config', 'statistics', 'system_logs');
```

**Resultado esperado:** 6 linhas

## 📊 Diagrama

Consulte: `/diagrams/database-diagram.puml`

---

**EcoVision** - Sistema de Reciclagem Inteligente 🌱♻️
