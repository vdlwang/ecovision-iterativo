# 🚀 Instalação e Execução do EcoVision

## ⚡ Quick Start - 3 Passos

### 1️⃣ Instalar Dependências Python

```bash
pip install -r requirements.txt
```

**Arquivo requirements.txt contém:**
- ultralytics (YOLO)
- opencv-python
- numpy
- flask
- flask-cors
- pillow

### 2️⃣ Baixar Modelos YOLO

Coloque os arquivos `.pt` na pasta `models/`:

```
models/
├── yolov8n.pt    # Modelo nano (mais rápido)
├── yolov8s.pt    # Modelo small (balanceado)
└── yolov8m.pt    # Modelo medium (mais preciso)
```

**Download dos modelos:**
- https://github.com/ultralytics/assets/releases

Ou deixe o script baixar automaticamente na primeira execução.

### 3️⃣ Executar o Sistema

#### **Linux/Mac:**
```bash
chmod +x run_dev.sh
./run_dev.sh
```

#### **Windows:**
```bash
run_dev.bat
```

Ou manualmente:

```bash
# Terminal 1 - Servidor de Inferência Python
python inference_server.py

# Terminal 2 - Aplicação Web (se necessário)
npm install
npm run dev
```

---

## 🌐 Acesso

Após iniciar, abra no navegador:

```
http://localhost:5000
```

**IMPORTANTE:** 
- ✅ Funciona em `localhost` (HTTP permitido para câmera)
- ✅ Funciona em produção com **HTTPS obrigatório**
- ❌ Não funciona em HTTP remoto (navegador bloqueia câmera)

---

## 📋 Checklist de Funcionamento

- [ ] Servidor Python rodando na porta 5000
- [ ] Modelos YOLO (.pt) na pasta `models/`
- [ ] Navegador aberto em `http://localhost:5000`
- [ ] Permissão de câmera concedida no navegador
- [ ] Sistema ligado (botão verde "Iniciar Sistema")
- [ ] Detecções aparecendo com bounding boxes coloridas

---

## 🎯 Fluxo de Operação

```
1. Usuário abre o site
   ↓
2. Sistema solicita permissão de câmera
   ↓
3. Usuário concede permissão
   ↓
4. Usuário clica em "Iniciar Sistema"
   ↓
5. Câmera captura frames (a cada 2 segundos)
   ↓
6. Frame enviado para servidor Python
   ↓
7. YOLO processa e detecta materiais
   ↓
8. Servidor retorna detecções com bounding boxes
   ↓
9. Interface desenha boxes coloridas na tela
   ↓
10. Cancelas abrem conforme configuração
```

---

## 🎨 Cores dos Materiais

| Material | Cor | Código |
|----------|-----|--------|
| 📄 Papel | Azul | `#163b6f` |
| 🔩 Metal | Verde | `#196626` |
| 🧴 Plástico | Vermelho | `#dc1f2e` |
| 🍾 Vidro | Amarelo | `#d2b91f` |

---

## 🔧 Configurações do Sistema

### Modelo YOLO
- **yolov8n**: Mais rápido, menos preciso (~10ms)
- **yolov8s**: Balanceado (~30ms)
- **yolov8m**: Mais preciso, mais lento (~80ms)

### Confiança Mínima
- Ajuste entre 30% e 95%
- Padrão recomendado: 60%

### Cancelas
- Configure até 3 cancelas
- Cada cancela pode filtrar múltiplos materiais
- Abre quando detecta material configurado

---

## 🐛 Troubleshooting

### Câmera não aparece
```
1. Verifique se está em HTTPS ou localhost
2. Clique no ícone de cadeado 🔒 na barra de URL
3. Permita acesso à câmera
4. Clique em "Tentar Novamente"
```

### Inferência não funciona
```
1. Verifique se inference_server.py está rodando
2. Confirme que os modelos .pt estão em models/
3. Verifique o console do navegador (F12)
4. Verifique logs do servidor Python
```

### Bounding boxes não aparecem
```
1. Certifique-se que o sistema está ligado (verde)
2. Verifique se a confiança mínima não está muito alta
3. Teste com objetos claros e bem iluminados
4. Verifique console para logs de detecção
```

---

## 📦 Estrutura de Pastas

```
EcoVision/
├── models/               # Modelos YOLO (.pt)
├── components/           # Componentes React
├── supabase/functions/   # Backend opcional
├── inference_server.py   # Servidor de inferência
├── requirements.txt      # Dependências Python
├── run_dev.sh           # Script Linux/Mac
└── run_dev.bat          # Script Windows
```

---

## ✅ Sistema Totalmente Funcional

O EcoVision está **100% funcional** quando executado localmente ou em produção HTTPS:

✅ **Captura de câmera em tempo real**  
✅ **Inferência YOLO com modelos Ultralytics**  
✅ **Detecção de 4 materiais recicláveis**  
✅ **Bounding boxes coloridas em tempo real**  
✅ **Controle de 3 cancelas independentes**  
✅ **Dashboard com estatísticas**  
✅ **Autenticação Google (opcional)**  

---

## 🚨 Importante

- **Playground Figma**: Limitado, pode ter erros de CORS/câmera
- **Localhost**: Funciona perfeitamente
- **Produção**: Requer HTTPS obrigatório para câmera

Para produção, faça deploy em:
- Vercel (frontend)
- Railway/Render (inference_server.py)
- Configure variáveis de ambiente corretamente
