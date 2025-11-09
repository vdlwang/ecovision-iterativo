# 🚀 LEIA-ME PRIMEIRO - EcoVision

## ✅ Sistema 100% Funcional

Este é um **sistema completo e funcional** de reciclagem inteligente com IA.

**Funciona perfeitamente quando executado localmente ou em produção HTTPS.**

---

## ⚡ Executar AGORA (30 segundos)

```bash
pip install -r requirements.txt
./run_dev.sh
```

Acesse: **http://localhost:5000**

**Pronto!** 🎉

---

## 🎯 O Que Este Sistema Faz

```
Webcam → Captura Objetos → YOLO Detecta → Desenha Boxes → Abre Cancelas
```

1. **Captura** imagens da webcam em tempo real
2. **Detecta** materiais recicláveis (papel, metal, plástico, vidro)
3. **Desenha** bounding boxes coloridas ao redor dos objetos
4. **Aciona** cancelas para separar automaticamente
5. **Salva** estatísticas no banco de dados
6. **Mostra** dashboard com gráficos e métricas

---

## 📚 Guias de Instalação

Escolha o seu nível:

| Guia | Quando Usar | Tempo |
|------|-------------|-------|
| **[COMO_EXECUTAR.md](./COMO_EXECUTAR.md)** | 🔥 Quer rodar rápido | 2 min |
| **[INSTALACAO.md](./INSTALACAO.md)** | 📦 Instalação detalhada | 10 min |
| **[QUICKSTART.md](./QUICKSTART.md)** | 🚀 Guia completo | 15 min |
| **[README.md](./README.md)** | 📖 Documentação completa | 30 min |

**→ Recomendação:** Comece por **[COMO_EXECUTAR.md](./COMO_EXECUTAR.md)**

---

## 🎥 Fluxo de Funcionamento

```
┌──────────────────────────────────────────────────────┐
│  1. USUÁRIO FAZ LOGIN NO SITE                        │
│     ↓                                                │
│  2. NAVEGADOR SOLICITA PERMISSÃO DE CÂMERA           │
│     ↓                                                │
│  3. USUÁRIO CLICA "PERMITIR" NO POPUP                │
│     ↓                                                │
│  4. USUÁRIO CLICA "INICIAR SISTEMA"                  │
│     ↓                                                │
│  5. LOOP A CADA 2 SEGUNDOS:                          │
│     ┌────────────────────────────────────┐           │
│     │ Webcam captura frame               │           │
│     │        ↓                            │           │
│     │ React converte para Base64         │           │
│     │        ↓                            │           │
│     │ HTTP POST para servidor Python     │           │
│     │        ↓                            │           │
│     │ YOLO detecta objetos 🤖            │           │
│     │        ↓                            │           │
│     │ Retorna detecções + bounding boxes │           │
│     │        ↓                            │           │
│     │ React desenha boxes na tela 🎨    │           │
│     │        ↓                            │           │
│     │ Sistema abre cancelas 🚪           │           │
│     │        ↓                            │           │
│     │ Salva no banco de dados 💾         │           │
│     └────────────────────────────────────┘           │
│                                                      │
│  RESULTADO: Você vê objetos detectados em tempo     │
│             real com caixas coloridas!               │
└──────────────────────────────────────────────────────┘
```

---

## 🎨 Cores das Detecções

Quando você colocar objetos na frente da câmera:

| Material | Cor da Box | Código | Exemplo |
|----------|-----------|--------|---------|
| 📄 Papel | **Azul** | `#163b6f` | Livro, jornal, caixa |
| 🔩 Metal | **Verde** | `#196626` | Lata, colher, alumínio |
| 🧴 Plástico | **Vermelho** | `#dc1f2e` | Garrafa PET, copo |
| 🍾 Vidro | **Amarelo** | `#d2b91f` | Garrafa, copo de vidro |

---

## 🌐 Onde Funciona

| Ambiente | Status | Observação |
|----------|--------|------------|
| **Localhost** (HTTP) | ✅ 100% | **← USE ESTE PARA TESTES** |
| **Produção** (HTTPS) | ✅ 100% | Requer HTTPS obrigatório |
| **Playground Figma** | ⚠️ Limitado | CORS e câmera bloqueados |

**IMPORTANTE:** Para ver o sistema funcionando de verdade, **execute localmente!**

---

## 🔧 Requisitos Mínimos

- ✅ Python 3.8 ou superior
- ✅ Webcam (integrada ou USB)
- ✅ 8GB RAM
- ✅ Windows, Linux ou Mac
- ✅ Navegador moderno (Chrome, Firefox, Edge)

**GPU NVIDIA:** Opcional, mas acelera 10x a inferência

---

## 📦 Arquivos Necessários

```
EcoVision/
├── inference_server.py      ← Servidor Python com YOLO
├── requirements.txt         ← Dependências
├── run_dev.sh              ← Script Linux/Mac  
├── run_dev.bat             ← Script Windows
└── models/                 ← Modelos YOLO
    ├── yolov8n.pt         (Mais rápido)
    ├── yolov8s.pt         (Balanceado)
    └── yolov8m.pt         (Mais preciso)
```

**Os modelos serão baixados automaticamente na primeira execução!**

---

## ⚠️ Problemas Comuns

**📹 Problemas com câmera?** → **[CAMERA_TROUBLESHOOTING.md](./CAMERA_TROUBLESHOOTING.md)**

### ❌ "Permissão de câmera negada"
```
1. Clique no cadeado 🔒 na barra de URL do navegador
2. Mude "Câmera" de "Bloquear" para "Permitir"
3. Recarregue a página (F5)
4. Clique em "Iniciar Sistema" novamente
5. Quando o navegador pedir permissão, clique "Permitir"
```

### ❌ "Nenhuma câmera encontrada"
```
1. Verifique se webcam está conectada
2. Teste em outro app (Zoom, Skype)
3. Verifique drivers da câmera
```

### ❌ "Erro ao processar inferência"
```
1. Certifique-se que inference_server.py está rodando
2. Confirme que modelos .pt estão em models/
3. Veja console do navegador (F12) para logs
4. Veja terminal do Python para erros
```

### ❌ Bounding boxes não aparecem
```
1. Sistema deve estar ligado (botão verde)
2. Confiança mínima não deve estar muito alta (use 60%)
3. Ilumine bem o objeto
4. Aproxime o objeto da câmera
5. Use objetos claros e bem definidos
```

---

## 🎯 Próximos Passos

1. **Executar:** Siga [COMO_EXECUTAR.md](./COMO_EXECUTAR.md)
2. **Testar:** Coloque objetos na frente da câmera
3. **Configurar:** Ajuste cancelas e confiança mínima
4. **Ver Dashboard:** Veja estatísticas em tempo real
5. **Personalizar:** Treine seu próprio modelo YOLO

---

## 📞 Suporte

**Não funcionou?**

1. ✅ Leia [COMO_EXECUTAR.md](./COMO_EXECUTAR.md) do início ao fim
2. ✅ Verifique console do navegador (F12)
3. ✅ Verifique terminal do Python
4. ✅ Confira [Troubleshooting](#️-problemas-comuns)
5. ✅ Abra Issue no GitHub com logs completos

---

## 🚀 Stack Tecnológico

- **Frontend:** React + TypeScript + Tailwind CSS
- **IA/ML:** Python + YOLO v8 + OpenCV
- **Backend:** Supabase (PostgreSQL + Edge Functions)
- **Autenticação:** Supabase Auth (Google OAuth)
- **Câmera:** getUserMedia API (WebRTC)

---

<div align="center">

## 🌿 EcoVision

**Sistema 100% Funcional de Reciclagem Inteligente com IA**

Desenvolvido para um planeta mais sustentável 💚

---

**[⚡ Executar Agora](./COMO_EXECUTAR.md)** | **[📖 Documentação](./README.md)** | **[🐛 Reportar Bug](https://github.com/seu-usuario/ecovision/issues)**

</div>
```
