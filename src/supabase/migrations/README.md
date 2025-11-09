# 🗄️ Migrações - EcoVision Database

**NOTA:** O EcoVision usa um sistema **KV Store** (chave-valor) flexível. Não requer migrations complexas.

---

## ✅ Tabela Principal

```sql
-- Tabela KV Store (já existe no Supabase)
kv_store_ea835390 (
  key TEXT PRIMARY KEY,
  value JSONB,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
)
```

Esta tabela armazena:
- Configurações do sistema
- Detecções de IA
- Estatísticas de usuários
- Histórico de sessões
- Dados de perfil

---

## 🚀 Setup (Opcional)

O sistema funciona **automaticamente** sem migrations. 

Se quiser criar tabelas estruturadas (opcional):

1. Acesse [Supabase Dashboard](https://supabase.com/dashboard)
2. SQL Editor → New Query
3. Execute: `001_create_ecovision_tables.sql` (se existir)

---

## ⚠️ Importante

- **Não** é necessário executar migrations manualmente
- Sistema KV funciona out-of-the-box
- Migrations estruturadas são opcionais
- Supabase gerencia a tabela KV automaticamente

---

**EcoVision** - Sistema de Reciclagem Inteligente 🌱
