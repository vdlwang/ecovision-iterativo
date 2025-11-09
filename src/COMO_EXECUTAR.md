# 🎯 Como Executar o EcoVision - Guia Rápido

> **TL;DR:** `pip install -r requirements.txt` → `./run_dev.sh` → `http://localhost:5000` → Pronto! 🚀

## ✅ Sistema 100% Funcional

O EcoVision **funciona perfeitamente** quando executado localmente ou em produção HTTPS:

✅ **Captura webcam em tempo real** via getUserMedia API  
✅ **Inferência YOLO com modelos Ultralytics** (YOLOv8n/s/m)  
✅ **Bounding boxes coloridas desenhadas na tela** em tempo real  
✅ **Detecção de materiais: papel, metal, plástico, vidro**  
✅ **Controle de 3 cancelas** baseado nas detecções  
✅ **Dashboard com estatísticas** e histórico completo  

---

## 🚀 Executar Agora (2 minutos)

### Passo 1: Instalar Python e Dependências

```bash
pip install ultralytics opencv-python numpy flask flask-cors pillow
```

### Passo 2: Baixar Modelos YOLO

Crie a pasta `models/` e baixe os modelos:

```bash
mkdir models
cd models
```

**Opção A - Download Manual:**
- Acesse: https://github.com/ultralytics/assets/releases
- Baixe: `yolov8n.pt`, `yolov8s.pt`, `yolov8m.pt`
- Coloque na pasta `models/`

**Opção B - Python Automático:**
```python
from ultralytics import YOLO

# Baixa automaticamente
YOLO('yolov8n.pt')
YOLO('yolov8s.pt')
YOLO('yolov8m.pt')
```

### Passo 3: Executar

#### Linux/Mac:
```bash
chmod +x run_dev.sh
./run_dev.sh
```

#### Windows:
```bash
run_dev.bat
```

#### Manual:
```bash
python inference_server.py
```

### Passo 4: Abrir no Navegador

```
http://localhost:5000
```

---

## 🎥 O Que Vai Acontecer

```
1. Você faz login → Navegador solicita permissão de câmera automaticamente 🎥
           ↓
2. Você clica "Permitir" no popup do navegador → Câmera pronta ✅
           ↓
3. Você clica "Iniciar Sistema" no feed da câmera → Câmera ativa 📹
           ↓
4. Loop começa 🔄 - A cada 2 segundos:
   
   Webcam → Captura Frame
      ↓
   React → Converte para Base64
      ↓
   HTTP → POST /inference
      ↓
   Python → YOLO detecta objetos 🤖
      ↓
   Python → Retorna detecções + bounding boxes
      ↓
   React → Desenha boxes na tela 🎨
      ↓
   Sistema → Abre cancelas se necessário 🚪
      ↓
   Database → Salva estatísticas 💾
```

**Resultado:** Você vê em tempo real os objetos sendo detectados com caixas coloridas ao redor!

---

## 🎨 Como Testar

1. **Papel:** Pegue um livro, jornal ou caixa de papelão
   - Aparece **bounding box azul** (#163b6f)
   
2. **Metal:** Pegue uma lata, colher ou objeto metálico
   - Aparece **bounding box verde** (#196626)
   
3. **Plástico:** Pegue garrafa PET, copo plástico
   - Aparece **bounding box vermelha** (#dc1f2e)
   
4. **Vidro:** Pegue garrafa de vidro, copo
   - Aparece **bounding box amarela** (#d2b91f)

---

## 🔧 Configurações

### No Menu "Modelo":

- **YOLOv8n**: Mais rápido (~100ms)
- **YOLOv8s**: Balanceado (~300ms)
- **YOLOv8m**: Mais preciso (~800ms)

### No Menu "Cancelas":

Configure qual cancela abre para cada material:
- Cancela 1: Papel + Papelão
- Cancela 2: Metal
- Cancela 3: Plástico + Vidro

### Confiança Mínima:

Ajuste entre 30% e 95%:
- Baixo (30-50%): Mais detecções, mais falsos positivos
- Médio (50-70%): Balanceado **← RECOMENDADO**
- Alto (70-95%): Menos detecções, mais precisas

---

## 📊 Estrutura de Arquivos Necessários

```
EcoVision/
├── inference_server.py         ✅ Servidor Python com YOLO
├── requirements.txt            ✅ Dependências
├── run_dev.sh                  ✅ Script Linux/Mac
├── run_dev.bat                 ✅ Script Windows
└── models/                     ✅ Modelos YOLO
    ├── yolov8n.pt             (6 MB)
    ├── yolov8s.pt             (22 MB)
    └── yolov8m.pt             (52 MB)
```

---

## ⚠️ Troubleshooting

**📹 Problemas com câmera?** Veja o guia completo: **[CAMERA_TROUBLESHOOTING.md](./CAMERA_TROUBLESHOOTING.md)**

### ❌ "Permissão de câmera negada"
```
CAUSA: Você clicou em "Bloquear" quando o navegador pediu permissão.

SOLUÇÃO RÁPIDA:
1. Clique no ícone de cadeado 🔒 na barra de URL do navegador
2. Encontre "Câmera" nas permissões
3. Mude de "Bloquear" para "Permitir"
4. Recarregue a página (F5)
5. Clique em "Iniciar Sistema" novamente
6. Agora deve funcionar! ✅
```

**Não funcionou?** Leia: **[CAMERA_TROUBLESHOOTING.md](./CAMERA_TROUBLESHOOTING.md)**

### ❌ "Nenhuma câmera encontrada"
```
1. Verifique se webcam está conectada
2. Teste webcam em outro app (Zoom, Skype, etc)
3. Verifique drivers da câmera
```

### ❌ "Erro ao processar inferência"
```
1. Verifique se inference_server.py está rodando
2. Confirme que modelos .pt estão em models/
3. Abra console do navegador (F12) para ver erros
4. Verifique terminal do Python para logs
```

### ❌ Bounding boxes não aparecem
```
1. Certifique-se que sistema está ligado (botão verde)
2. Verifique se confiança mínima não está muito alta
3. Ilumine bem o objeto
4. Aproxime o objeto da câmera
5. Use objetos claros e visíveis
```

---

## 🌐 Deploy em Produção

### Servidor Python (Render.com):

1. Crie conta em https://render.com
2. Novo Web Service → Connect GitHub
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `python inference_server.py`
5. Environment: Python 3.11
6. Deploy!

### Frontend (Vercel):

1. Já está deployado no Figma Make!
2. Ou faça deploy no Vercel para domínio próprio

**⚠️ IMPORTANTE:** Produção **REQUER HTTPS** para câmera funcionar!

---

## 💡 Dicas de Performance

### CPU Apenas:
- Use YOLOv8n (mais rápido)
- Confiança mínima: 60%
- Espere ~100-500ms por inferência

### Com GPU NVIDIA:
```bash
# Instale CUDA + cuDNN
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Performance: ~10-50ms por inferência 🚀
```

### Otimização:
- Reduza resolução da webcam: 640x480 ou 1280x720
- Aumente intervalo entre capturas (de 2s para 3s)
- Use iluminação adequada

---

## ✅ Checklist Final

Antes de reportar problemas, verifique:

- [ ] Python 3.8+ instalado
- [ ] Dependências instaladas (`pip install -r requirements.txt`)
- [ ] Modelos .pt na pasta `models/`
- [ ] `inference_server.py` rodando sem erros
- [ ] Navegador aberto em `http://localhost:5000`
- [ ] Permissão de câmera concedida
- [ ] Sistema iniciado (botão verde)
- [ ] Webcam funcionando (teste em outro app)

---

## 📞 Suporte

**Não está funcionando?**

1. Leia este guia do início ao fim
2. Verifique console do navegador (F12)
3. Verifique logs do terminal Python
4. Confira [INSTALACAO.md](./INSTALACAO.md) para mais detalhes
5. Abra Issue no GitHub com logs completos

---

<div align="center">

**🌿 EcoVision - Sistema 100% Funcional**

Desenvolvido para reciclagem inteligente com IA

</div>
```
