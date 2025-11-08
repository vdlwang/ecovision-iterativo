# EcoVision - Documentação da API

## 📡 Endpoints da API

Base URL: `https://{projectId}.supabase.co/functions/v1/make-server-ea835390`

Todos os endpoints requerem o header:
```
Authorization: Bearer {publicAnonKey}
```

---

## 🏥 Health Check

### GET /health

Verifica se o servidor está funcionando.

**Response:**
```json
{
  "status": "ok",
  "message": "EcoVision server is running"
}
```

---

## ⚙️ Configuração do Sistema

### POST /config

Salva configurações do sistema.

**Request Body:**
```json
{
  "gateConfigs": {
    "1": "papel",
    "2": "plastico",
    "3": "metal"
  },
  "minAccuracy": 85,
  "modelVersion": "YOLOv8s"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Configuração salva com sucesso"
}
```

### GET /config

Obtém configurações do sistema.

**Response:**
```json
{
  "success": true,
  "config": {
    "gateConfigs": { "1": "papel", "2": "plastico", "3": "metal" },
    "minAccuracy": 85,
    "modelVersion": "YOLOv8s",
    "updatedAt": "2025-01-19T12:00:00.000Z"
  }
}
```

---

## 🎚️ Controle da Esteira

### POST /esteira/ligar

Liga a esteira rolante.

**Response:**
```json
{
  "success": true,
  "status": "ligada"
}
```

### POST /esteira/desligar

Desliga a esteira rolante.

**Response:**
```json
{
  "success": true,
  "status": "desligada"
}
```

---

## 🚪 Controle das Cancelas

### POST /cancela/:id/abrir

Abre uma cancela específica.

**Params:**
- `id`: ID da cancela (1, 2 ou 3)

**Response:**
```json
{
  "success": true,
  "status": "aberta"
}
```

### POST /cancela/:id/fechar

Fecha uma cancela específica.

**Params:**
- `id`: ID da cancela (1, 2 ou 3)

**Response:**
```json
{
  "success": true,
  "status": "fechada"
}
```

**Exemplo:**
```bash
curl -X POST https://seu-projeto.supabase.co/functions/v1/make-server-ea835390/cancela/1/abrir \
  -H "Authorization: Bearer sua-anon-key"
```

---

## 📹 Controle da Câmera

### POST /camera/iniciar

Inicia o stream da câmera.

**Response:**
```json
{
  "success": true,
  "ativa": true
}
```

### POST /camera/parar

Para o stream da câmera.

**Response:**
```json
{
  "success": true,
  "ativa": false
}
```

### GET /camera/capturar

Captura um frame da câmera.

**Response:**
```json
{
  "success": true,
  "frame": {
    "timestamp": "2025-01-19T12:00:00.000Z",
    "data": "frame_data"
  }
}
```

---

## 🤖 Controle do Modelo IA

### POST /modelo/ativar

Ativa o modelo de IA.

**Response:**
```json
{
  "success": true,
  "ativo": true
}
```

### POST /modelo/desativar

Desativa o modelo de IA.

**Response:**
```json
{
  "success": true,
  "ativo": false
}
```

### POST /modelo/calibrar

Calibra o limite mínimo de acurácia do modelo.

**Request Body:**
```json
{
  "limite": 90
}
```

**Response:**
```json
{
  "success": true,
  "limiteAtual": 90
}
```

### POST /modelo/processar

Processa um frame com o modelo IA.

**Request Body:**
```json
{
  "frame": { "timestamp": "...", "data": "..." },
  "gateConfigs": {
    "1": "papel",
    "2": "plastico",
    "3": "metal"
  }
}
```

**Response:**
```json
{
  "success": true,
  "predicao": {
    "classe": "plastico",
    "confianca": 92.5
  },
  "acionamentos": [2]
}
```

---

## 📊 Dashboard e Estatísticas

### GET /dashboard/visao-geral

Obtém visão geral do sistema.

**Response:**
```json
{
  "success": true,
  "dados": {
    "totalProcessados": 1250,
    "materiais": {
      "papel": 320,
      "metal": 280,
      "plastico": 420,
      "vidro": 230
    },
    "performanceCancelas": {
      "cancela_1": 320,
      "cancela_2": 420,
      "cancela_3": 280
    },
    "precisaoMedia": 87.5,
    "data": "2025-01-19T12:00:00.000Z"
  }
}
```

### GET /dashboard/status

Obtém status geral do sistema.

**Response:**
```json
{
  "success": true,
  "status": {
    "sistema": "EcoVision",
    "versao": "1.0.0",
    "status": "operacional",
    "timestamp": "2025-01-19T12:00:00.000Z"
  }
}
```

### GET /dashboard/materiais

Obtém estatísticas de materiais processados hoje.

**Response:**
```json
{
  "success": true,
  "materiais": {
    "papel": 320,
    "metal": 280,
    "plastico": 420,
    "vidro": 230
  }
}
```

### GET /dashboard/performance-cancelas

Obtém performance das cancelas hoje.

**Response:**
```json
{
  "success": true,
  "performance": {
    "cancela_1": 320,
    "cancela_2": 420,
    "cancela_3": 280
  }
}
```

---

## 🔐 Autenticação

### POST /auth/login

Faz login com token do Google.

**Request Body:**
```json
{
  "token": "google_oauth_token"
}
```

**Response:**
```json
{
  "success": true,
  "sessionId": "session_1234567890",
  "usuario": {
    "id": "user_1234567890",
    "name": "João Silva",
    "email": "joao@example.com",
    "autenticado": true
  }
}
```

### POST /auth/logout

Faz logout do usuário.

**Request Body:**
```json
{
  "email": "joao@example.com"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Logout realizado"
}
```

### GET /auth/verificar/:email

Verifica se um usuário está autenticado.

**Params:**
- `email`: Email do usuário

**Response:**
```json
{
  "success": true,
  "autenticado": true
}
```

---

## 📝 Detecções

### POST /detections

Registra uma nova detecção.

**Request Body:**
```json
{
  "material": "plastico",
  "confidence": 92.5,
  "gateAssigned": 2,
  "timestamp": "2025-01-19T12:00:00.000Z"
}
```

**Response:**
```json
{
  "success": true,
  "id": "detection_1234567890"
}
```

### GET /stats

Obtém estatísticas de detecções.

**Response:**
```json
{
  "success": true,
  "stats": {
    "total": 1250,
    "byMaterial": {
      "papel": 320,
      "metal": 280,
      "plastico": 420,
      "vidro": 230
    },
    "byGate": {
      "1": 320,
      "2": 420,
      "3": 280
    }
  }
}
```

---

## 📋 Logs

### POST /logs

Registra um log do sistema.

**Request Body:**
```json
{
  "type": "info",
  "message": "Sistema iniciado",
  "details": { "usuario": "admin" }
}
```

**Response:**
```json
{
  "success": true,
  "id": "log_1234567890"
}
```

### GET /logs

Obtém todos os logs do sistema.

**Response:**
```json
{
  "success": true,
  "logs": [
    {
      "type": "info",
      "message": "Sistema iniciado",
      "details": { "usuario": "admin" },
      "createdAt": "2025-01-19T12:00:00.000Z"
    }
  ]
}
```

---

## 🔴 Códigos de Erro

| Código | Descrição |
|--------|-----------|
| 200 | Sucesso |
| 400 | Requisição inválida |
| 401 | Não autorizado |
| 404 | Recurso não encontrado |
| 500 | Erro interno do servidor |

**Exemplo de Erro:**
```json
{
  "success": false,
  "error": "Descrição do erro"
}
```

---

## 🧪 Testando a API

### Com cURL:

```bash
# Health check
curl https://seu-projeto.supabase.co/functions/v1/make-server-ea835390/health

# Obter configuração
curl -H "Authorization: Bearer sua-anon-key" \
  https://seu-projeto.supabase.co/functions/v1/make-server-ea835390/config

# Ligar esteira
curl -X POST \
  -H "Authorization: Bearer sua-anon-key" \
  https://seu-projeto.supabase.co/functions/v1/make-server-ea835390/esteira/ligar
```

### Com JavaScript (Frontend):

```javascript
import { projectId, publicAnonKey } from './utils/supabase/info';

const baseUrl = `https://${projectId}.supabase.co/functions/v1/make-server-ea835390`;

// Ligar esteira
const response = await fetch(`${baseUrl}/esteira/ligar`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${publicAnonKey}`,
    'Content-Type': 'application/json'
  }
});

const data = await response.json();
console.log(data);
```

### Com Python:

```python
import requests

base_url = "https://seu-projeto.supabase.co/functions/v1/make-server-ea835390"
headers = {
    "Authorization": "Bearer sua-anon-key",
    "Content-Type": "application/json"
}

# Ligar esteira
response = requests.post(f"{base_url}/esteira/ligar", headers=headers)
print(response.json())
```

---

## 📚 Recursos Adicionais

- [Documentação Supabase](https://supabase.com/docs)
- [Documentação Hono](https://hono.dev)
- [Documentação Deno](https://deno.land/manual)

---

**EcoVision API v1.0** - Sistema de Controle Inteligente para Centro de Reciclagem
