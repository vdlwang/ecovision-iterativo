# EcoVision - Sistema de Controle para Esteira Rolante de Centro de Reciclagem

## 🎯 Visão Geral

O EcoVision é um sistema integrado de controle de esteira rolante para centros de reciclagem, que utiliza Inteligência Artificial (modelos YOLO da Ultralytics) para identificar e separar automaticamente materiais recicláveis através de até 3 cancelas.

### Materiais Detectados
- **Papel/Papelão** (azul #163b6f)
- **Metal** (verde #196626)
- **Plástico** (vermelho #dc1f2e)
- **Vidro** (amarelo #d2b91f)

## 🚀 Como Usar

### 1. Preparação dos Modelos de IA

#### a) Treine seus modelos YOLO
Você precisa treinar 3 versões do modelo YOLO (YOLOv8) para detectar os 4 materiais:

```bash
# Exemplo de treinamento com Ultralytics
from ultralytics import YOLO

# Treinar YOLOv8n (nano - mais rápido)
model = YOLO('yolov8n.pt')
model.train(data='recycling_data.yaml', epochs=100, imgsz=640)

# Treinar YOLOv8s (small - balanceado)
model = YOLO('yolov8s.pt')
model.train(data='recycling_data.yaml', epochs=100, imgsz=640)

# Treinar YOLOv8m (medium - mais preciso)
model = YOLO('yolov8m.pt')
model.train(data='recycling_data.yaml', epochs=100, imgsz=640)
```

#### b) Estrutura do dataset (recycling_data.yaml)
```yaml
path: ./recycling_dataset
train: images/train
val: images/val
test: images/test

names:
  0: papel
  1: metal
  2: plastico
  3: vidro
```

#### c) Coloque os modelos treinados na pasta
Após o treinamento, mova os arquivos `.pt` para a pasta `/models/`:
```
/models/
  ├── yolov8n.pt  (nano)
  ├── yolov8s.pt  (small)
  └── yolov8m.pt  (medium)
```

### 2. Instalar Dependências Python

```bash
pip install ultralytics flask flask-cors opencv-python pillow
```

### 3. Iniciar Servidor de Inferência

```bash
python inference_server.py
```

O servidor ficará disponível em `http://localhost:5000`

**Logs esperados:**
```
[MODELO] Carregando ./models/yolov8n.pt...
[MODELO] yolov8n carregado com sucesso!
[INFO] Iniciando servidor na porta 5000...
```

### 4. Iniciar Frontend

O frontend já está configurado e se conectará automaticamente ao servidor de inferência.

**IMPORTANTE:** Para usar câmeras reais, você precisa:
- Permitir acesso à câmera no navegador
- Ter pelo menos uma webcam conectada ao dispositivo
- O navegador deve estar em HTTPS ou localhost

## 🔧 Configuração do Hardware (ESP32)

### Comunicação Serial

O sistema envia comandos para um ESP32 via porta serial:

**Formato do comando:** 3 bits
- **Bit 0:** Estado da esteira (0 = desligada, 1 = ligada)
- **Bits 1-2:** Número da cancela (01 = cancela 1, 10 = cancela 2, 11 = cancela 3)

**Exemplos:**
- `001` (binário) = Esteira ligada, nenhuma cancela
- `011` (binário) = Esteira ligada, cancela 1 ativa
- `101` (binário) = Esteira ligada, cancela 2 ativa
- `111` (binário) = Esteira ligada, cancela 3 ativa

### Código ESP32 (exemplo)

```cpp
void setup() {
  Serial.begin(9600);
  pinMode(ESTEIRA_PIN, OUTPUT);
  pinMode(CANCELA1_PIN, OUTPUT);
  pinMode(CANCELA2_PIN, OUTPUT);
  pinMode(CANCELA3_PIN, OUTPUT);
}

void loop() {
  if (Serial.available() > 0) {
    byte command = Serial.read();
    
    // Bit 0: Esteira
    bool esteira = command & 0b001;
    digitalWrite(ESTEIRA_PIN, esteira ? HIGH : LOW);
    
    // Bits 1-2: Cancela
    byte cancela = (command >> 1) & 0b11;
    
    digitalWrite(CANCELA1_PIN, cancela == 1 ? HIGH : LOW);
    digitalWrite(CANCELA2_PIN, cancela == 2 ? HIGH : LOW);
    digitalWrite(CANCELA3_PIN, cancela == 3 ? HIGH : LOW);
  }
}
```

## 📊 Estrutura do Banco de Dados

O sistema usa Supabase com tabela KV (key-value) para armazenar:

### Detecções
**Chave:** `detection_{userId}_{timestamp}`
```json
{
  "userId": "user-id",
  "material": "papel|metal|plastico|vidro",
  "confidence": 95.5,
  "gateAssigned": 1,
  "timestamp": "2025-01-08T10:30:00Z",
  "createdAt": "2025-01-08T10:30:00Z"
}
```

### Configurações do Sistema
**Chave:** `system_config`
```json
{
  "gateConfigs": {
    "1": "papel",
    "2": "plastico",
    "3": "metal"
  },
  "minAccuracy": 85,
  "modelVersion": "YOLOv8n",
  "updatedAt": "2025-01-08T10:00:00Z"
}
```

### Configuração Favorita do Usuário
**Chave:** `user_{userId}_favorite_config`
```json
{
  "cancela1": "papel",
  "cancela2": "plastico",
  "cancela3": "metal",
  "minAccuracy": 85,
  "modelVersion": "YOLOv8s"
}
```

## 🎮 Usando o Sistema

### 1. Login
- Faça login com sua conta Google (autenticação via Supabase Auth)

### 2. Monitor (Tela Principal)
- **Esteira:** Visualização da esteira rolante (esquerda)
- **Câmera:** Stream ao vivo da webcam com bounding boxes (direita)
- **Seletor de Câmera:** Escolha qual câmera usar
- **Botão Iniciar/Parar:** Controla o sistema
- **Detecções Recentes:** Lista das últimas 10 detecções

### 3. Configuração de Cancelas
Configure qual material cada cancela deve separar:
- Cancela 1, 2 ou 3
- Material: papel, metal, plástico ou vidro

### 4. Modelo de IA
- **Versão do Modelo:** Escolha entre YOLOv8n, YOLOv8s ou YOLOv8m
- **Confiança Mínima:** Ajuste o limite (padrão: 85%)
  - Detecções abaixo deste limite serão rejeitadas

### 5. Dashboard
- Estatísticas em tempo real por usuário
- Gráficos de performance
- Distribuição de materiais
- Performance das cancelas
- Botão de atualizar dados

### 6. Perfil
- Informações do usuário
- Total de sessões e detecções
- Configuração mais utilizada
- Histórico de execuções

## 🔍 Logs do Sistema

O sistema registra logs detalhados no console:

### Logs de Câmera
```
[CÂMERA] 2 câmera(s) detectada(s): ["HD Webcam", "USB Camera"]
[CÂMERA] Stream iniciada - Câmera: HD Webcam
```

### Logs de Inferência
```
[INFERÊNCIA] Enviando frame para modelo yolov8n (confiança mínima: 85%)
[INFERÊNCIA] 1 detecção(ões): plastico (92.3%)
```

### Logs de Detecção
```
[DETECÇÃO] Material: plastico, Confiança: 92.3%
[CANCELA] Acionando cancela 2 para plastico
```

### Logs Seriais
```
[SERIAL] Enviando comando - Esteira: ON, Cancela: 2
[SERIAL] Comando enviado: 101 (binário) - Resposta: OK
```

### Logs de Banco de Dados
```
[BD] Detecção salva: plastico (92.3%) - Usuário: user-123
[BD] Detecção registrada para usuário user-123
```

### Logs de Dashboard
```
[DASHBOARD] Carregando estatísticas para usuário user-123
[DASHBOARD] Estatísticas: 45 processados, 38 separados
```

## 🛠️ Troubleshooting

### Câmera não funciona
1. Verifique se permitiu acesso à câmera no navegador
2. Certifique-se de que está usando HTTPS ou localhost
3. Teste com outra câmera
4. Verifique o console para erros

### Modelos não detectam nada
1. Verifique se os modelos .pt estão na pasta `/models/`
2. Confirme que os modelos foram treinados corretamente
3. Ajuste a confiança mínima (tente valores menores)
4. Verifique os logs do servidor Python

### ESP32 não responde
1. Verifique a conexão serial
2. Confirme a porta serial no backend
3. Teste a comunicação serial manualmente
4. O sistema funciona em modo simulação se serial não estiver disponível

### Dashboard não atualiza
1. Clique no botão "Atualizar"
2. Verifique se há detecções salvas no banco
3. Confirme que o userId está correto
4. Veja os logs do backend

## 📝 Notas Importantes

1. **Performance:** YOLOv8n é mais rápido mas menos preciso, YOLOv8m é mais preciso mas mais lento
2. **Confiança:** Valores muito altos (>90%) podem rejeitar muitas detecções válidas
3. **Câmera:** Iluminação adequada melhora drasticamente a detecção
4. **Hardware:** ESP32 é recomendado mas não obrigatório (sistema funciona em simulação)
5. **Dados:** Todas as detecções são salvas por usuário para análise posterior

## 🎨 Personalização

### Cores dos Materiais
Edite em `/styles/globals.css`:
```css
--material-paper: #163b6f;    /* Papel - Azul */
--material-metal: #196626;    /* Metal - Verde */
--material-plastic: #dc1f2e;  /* Plástico - Vermelho */
--material-glass: #d2b91f;    /* Vidro - Amarelo */
```

### Porta Serial
Configure no backend em `/supabase/functions/server/index.tsx`:
```typescript
const controlador = new ControladorSerial("/dev/ttyUSB0", 9600);
```

## 📦 Requisitos do Sistema

- **Frontend:** React, TypeScript, Tailwind CSS
- **Backend:** Supabase Edge Functions (Deno)
- **Inferência:** Python 3.8+, Ultralytics, Flask
- **Hardware (opcional):** ESP32, porta serial
- **Navegador:** Chrome/Edge/Firefox (com suporte a MediaDevices)

## 🔗 Endpoints da API

### Inferência
- `POST /api/inference` - Envia frame para análise

### Detecções
- `POST /make-server-ea835390/detections/save` - Salva detecção

### Dashboard
- `GET /make-server-ea835390/dashboard/stats?userId=X` - Estatísticas

### Serial
- `POST /make-server-ea835390/serial/send` - Envia comando

### Perfil
- `GET /make-server-ea835390/user/stats?userId=X` - Dados do usuário

## 🤝 Suporte

Para problemas ou dúvidas, verifique:
1. Logs do console do navegador
2. Logs do servidor Python
3. Logs do backend Supabase
4. Este arquivo de documentação

---

**Versão:** 2.0  
**Última Atualização:** 08 de Novembro de 2025
