# 📁 Modelos YOLO - EcoVision

**⚠️ PASTA VAZIA?** Os modelos não estão incluídos no repositório. Siga os passos abaixo.

---

## 🚀 SETUP RÁPIDO (3 Passos)

### ✅ Você JÁ TEM modelos .pt treinados no GitHub?

**PASSO 1:** Baixe/copie seus modelos para esta pasta
```bash
# Copie do seu repositório/local
cp /caminho/dos/modelos/*.pt ./

# Ou baixe do GitHub
wget https://github.com/seu-usuario/repo/raw/main/models/yolov8n.pt
```

**PASSO 2:** Converta para ONNX
```bash
# Na raiz do projeto (não nesta pasta)
cd ..
python convert_to_onnx.py models/yolov8n.pt --output yolov8n.onnx

# Move para pasta models/
mv yolov8n.onnx models/
```

**PASSO 3:** Inicie o sistema
```bash
./run_dev.sh  # Linux/Mac
# ou
run_dev.bat   # Windows

# Acesse http://localhost:5000
# Login → Monitor → Iniciar Sistema
# ✅ Bounding boxes aparecerão!
```

---

## 📋 STATUS DOS MODELOS

Após seguir os passos acima, você deve ter:

```
models/
├── yolov8n.pt      (seu modelo original)
└── yolov8n.onnx    (modelo convertido - NECESSÁRIO!)
```

**Verifique:**
```bash
ls -lh models/
# Deve mostrar yolov8n.onnx (~12MB)
```

---

## 🎯 Classes Esperadas

Seus modelos devem detectar 4 classes:

| ID | Material | Cor UI | Código Hex |
|----|----------|--------|------------|
| 0 | papel | Azul | #163b6f |
| 1 | metal | Verde | #196626 |
| 2 | plastico | Vermelho | #dc1f2e |
| 3 | vidro | Amarelo | #d2b91f |

**Importante:** O sistema espera essas 4 classes nessa ordem exata!

---

## 🔄 ALTERNATIVA: Servidor Python

Se não quiser usar ONNX no navegador:

1. **Coloque modelos .pt aqui:**
   ```bash
   cp /caminho/yolov8n.pt models/
   ```

2. **Inicie servidor:**
   ```bash
   python inference_server.py
   # Console mostrará: [INFO] Servidor rodando em http://0.0.0.0:8000
   ```

3. **Inicie frontend (outro terminal):**
   ```bash
   ./run_dev.sh
   ```

Sistema detectará servidor automaticamente.

---

## ❓ PROBLEMAS COMUNS

### "Nenhuma detecção aparece"

**Diagnóstico:**
1. Abra console do navegador (F12)
2. Procure por:
   - `[ONNX] ✅ Modelo carregado` → **Tudo OK!**
   - `[ONNX] ❌ Erro ao carregar` → **Modelo não encontrado**
   - `[INFERÊNCIA MOCK]` → **Sistema em modo demo**

**Solução:**
- Se vê "❌ Erro ao carregar": arquivo `yolov8n.onnx` não existe
- Se vê "MOCK": nem ONNX nem servidor Python funcionando
- Siga os 3 passos acima para corrigir

### "Erro ao converter modelo"

```bash
# Instale dependências
pip install ultralytics onnx

# Tente novamente
python convert_to_onnx.py models/yolov8n.pt
```

### "Modelo muito grande"

Use modelo nano para navegador:
- ✅ yolov8n.pt → yolov8n.onnx (~12MB) - **Ideal**
- ⚠️ yolov8s.pt → yolov8s.onnx (~45MB) - Lento
- ❌ yolov8m.pt → yolov8m.onnx (~100MB) - Muito lento

---

## 📚 DOCUMENTAÇÃO COMPLETA

Veja `/SETUP_MODELOS.md` na raiz do projeto para:
- Troubleshooting detalhado
- Conversão em lote
- Treinamento de novos modelos
- Configuração do servidor Python

---

## ✅ CHECKLIST

Antes de abrir issues, verifique:

- [ ] Arquivo `yolov8n.onnx` existe nesta pasta
- [ ] Tamanho do arquivo é ~10-15MB (ls -lh)
- [ ] Modelo tem 4 classes (papel, metal, plastico, vidro)
- [ ] Console não mostra erros de ONNX
- [ ] Câmera está permitida no navegador
- [ ] Sistema foi iniciado (botão "Iniciar Sistema")

---

**🆘 AINDA COM PROBLEMAS?**

Compartilhe os logs do console (F12) mostrando as mensagens `[ONNX]` e `[INFERÊNCIA]`.

---

**Última atualização:** 09 Nov 2025
