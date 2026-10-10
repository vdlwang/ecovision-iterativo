# Frontend - EcoVision

Interface web em React 18 + Vite para monitorar e configurar a esteira. Conversa com o backend por WebSocket em `ws://localhost:8765` (veja [`backend/README.md`](../backend/README.md)). Visão geral no [README principal](../README.md).

## Comandos

```bash
npm install
npm run dev       # http://localhost:5173
npm run build     # gera build/
npm run preview   # serve o build
```

As dependências estão fixadas no `package.json` e no `package-lock.json`. Não há checagem de tipos: o Vite só transpila o TypeScript.

O código veio de um export do Figma. Os componentes importam pacotes com versão no nome (`lucide-react@0.487.0`, `sonner@2.0.3`...), e os aliases em `vite.config.ts` resolvem esses nomes. Mantenha os aliases ao adicionar ou atualizar pacotes. `src/index.css` é Tailwind já compilado.

## Uso da interface

**Login:** "Google" e "Modo Demo" são simulados. Ambos só gravam um marcador no `localStorage`.

**Monitor em Tempo Real:** vídeo da câmera com as caixas detectadas, lista de detecções, FPS, botões para ligar e parar a esteira e indicador de conexão com o backend.

**Cancelas de Separação:** ângulo do servo para cada material (Plástico, Metal, Vidro, Papel). "Testar" move o servo para o ângulo escolhido, e "Salvar Configuração" grava `class_to_angle` em `backend/config.json`. Os ângulos passam a valer sem reiniciar o backend.

**Configuração do Modelo:** modelo, confiança mínima, porta serial, baud rate e índice da câmera. "Salvar Configuração" grava no `backend/config.json`. Depois é preciso **reiniciar o backend** para valer. "Testar Conexão Serial" liga o motor por 2 s e o desliga: serve só para conferir se o ESP32 responde.

## Problemas conhecidos

- O painel de cancelas grava a chave `vidro`, mas o backend procura `glass`. Por isso, depois de salvar, vidro deixa de ser separado.
- O seletor de modelo monta o caminho `../yolo_models/taco/<tipo>.pt`. "Small" aponta para o modelo COCO, "Nano" e "Medium" para os pesos TACO sem fine-tuning, e "Large" e "XLarge" para arquivos inexistentes. O modelo do projeto é o `best.pt` (veja [`yolo_models/README.md`](../yolo_models/README.md)).
- Os painéis pedem `get_config`, mas o backend não responde a essa mensagem. Por isso mostram valores fixos, não a configuração atual.

## Troubleshooting

**"Backend Offline":** confira se o backend está rodando e se a porta 8765 está livre (`python backend/test_connection.py`).
