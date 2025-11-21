# 🚀 Quick Start - EcoVision

## Início Rápido (3 minutos)

### 1️⃣ Instalar Dependências Backend

```bash
cd backend
pip install -r requirements.txt
```

### 2️⃣ Editar Configuração

Abra `config.json` e ajuste:

```json
{
  "serial_port": "COM7",  // ← Sua porta (Windows: COMx, Linux: /dev/ttyUSB0)
  "model_path": "../yolo_models/taco/yolov8s.pt"  // ← Seu modelo .pt
}
```

### 3️⃣ Testar Sistema

```bash
cd backend
python test_connection.py
```

Deve mostrar:
- ✓ Bibliotecas instaladas
- ✓ Câmera funcionando
- ✓ Portas seriais disponíveis
- ✓ Porta WebSocket livre

### 4️⃣ Iniciar Backend

```bash
python ecovision_local.py
```

Aguarde ver:
```
✓ WebSocket server rodando!
Stream YOLO iniciado!
```

### 5️⃣ Abrir Frontend

O frontend já está rodando no Figma Make. Ele se conecta automaticamente ao backend!

---

## ⚠️ Problemas Comuns

### "Serial port not found"
- Verifique se ESP32 está conectado via USB
- Ajuste `serial_port` no `config.json`

### "Câmera não abre"
- Ajuste `camera_index` no `config.json` (tente 0, 1, 2)

### "WebSocket não conecta"
- Certifique-se que o backend está rodando
- Deve mostrar "Backend Conectado" (badge verde) no frontend

### "Modelo não encontrado"
- Coloque seu modelo `.pt` em `../yolo_models/taco/`
- Ou use `yolov8s.pt` (baixa automaticamente)

---

## 📱 Como Usar

### Tela Monitor
- Veja detecções em tempo real
- Controle motor (Ligar/Parar)
- Ajuste confiança mínima do YOLO

### Tela Config. Modelo
- Configure ângulo do servo para cada material
- Teste cada posição individualmente

### Tela Config. Esteira
- Configure porta serial do ESP32
- Configure índice da câmera
- Teste conexão serial

---

## 🔧 Comandos Úteis

| Ação | Comando |
|------|---------|
| Testar conexões | `python backend/test_connection.py` |
| Iniciar backend | `python backend/ecovision_local.py` |
| Instalar deps | `pip install -r backend/requirements.txt` |

---

## 📦 Estrutura Mínima

```
ecovision/
├── backend/
│   ├── ecovision_local.py    ← Backend principal
│   ├── test_connection.py    ← Testes
│   └── requirements.txt      ← Dependências
├── config.json               ← Configuração central
└── components/               ← Frontend React
    ├── MonitorPanel.tsx
    ├── ConfigModelPanel.tsx
    └── ConfigConveyorPanel.tsx
```

---

## ✅ Checklist Rápido

- [ ] Python 3.8+ instalado
- [ ] Dependências instaladas (`pip install -r requirements.txt`)
- [ ] ESP32 conectado e porta configurada
- [ ] Webcam conectada
- [ ] Modelo YOLO (.pt) disponível
- [ ] Backend rodando (`python ecovision_local.py`)
- [ ] Frontend conectado (badge verde)

🎉 **Pronto!** Sistema operacional!
