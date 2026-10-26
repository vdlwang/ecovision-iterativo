# Refatoração — lista de trabalho (temporária)

Branch: `feature/refactoring-original-code`. Base de comparação: tag `tese-final` (`git diff tese-final -- <caminho>`).

**Tipos de mudança** (ordem de execução)

1. **L** — limpeza sem alterações: nenhum comportamento muda (código morto, logs, comentários, arquivos não usados).
2. **FS** — fix simples: corrige comportamento em poucas linhas, localizado.
3. **FC** — fix complexo: muda o fluxo, a concorrência ou a lógica de detecção; testar com hardware.
4. **P** — padronização com algumas mudanças: reorganiza ou unifica, com efeito pequeno e visível.
5. **D** — documentação: junto com cada mudança; os itens próprios ficam para o final.

Regra: commits de comportamento separados dos de limpeza, para `git diff tese-final` mostrar o que mudou de fato. A cada fix, atualizar "Limitações conhecidas" (`README.md`) e `CLAUDE.md` (item 27; o `PROBLEMAS.md` agora só guarda problemas fora do código).

**Status**: `[ ]` pendente · `[x]` feito (com hash) · `[~]` parcial · `—` não se aplica

---

## L — Limpeza sem alterações

| # | Status | Item | Ação |
|---|---|---|---|
| 7 | [x] `4a6ebd0` | Prints de debug por frame ou detecção (`send_line`, `broadcast`, `cls_ids`, "fora da ROI" impresso mesmo dentro etc.). | Removidos. O passo seguinte é o item 14. |
| 8 | [x] `4a6ebd0` | Imprime atalhos `(o)/(p)/(q)` que não existem. | Removido. |
| 15 | [x] `5198a85` | Backend duplicado: `ecovision_local.py` (fila), cerca de 95% igual ao `ecovision_local_modf.py`. | Apagado; está em `git show tese-final:backend/ecovision_local.py`. |
| 16 | [x] `55fd7da` | ~100 linhas de firmware antigo comentado, rampas comentadas em `motorControl`, `valor_pwm` sem uso. | Removidos. O `LED_PIN` sem uso virou o item 34. |
| 17 | [x] `667766a` | Sobras do Figma: 40 componentes `ui/`, 34 deps, aliases, `.npmrc`, imports mortos. | Removidos; o lock não muda versões e o CSS é idêntico. |

## FS — Fix simples

| # | Status | Problema | Onde | Correção |
|---|---|---|---|---|
| 1 | [x] `de008c6` | "Salvar" no painel Modelo grava os valores iniciais da UI (`model_path: ''`, `COM8`, `camera_index: 0`, `confidence: 0.4`), porque o backend não responde `get_config`. No próximo start, `YOLO('')` falha. O `save_config` também grava a chave `"type"`. | `ConfigModelPanel.tsx`, `ecovision_local_modf.py` (handler) | Responder `get_config` com `{**config, "type": "config"}`; não gravar `type` no save. |
| 2 | [x] `1b7cfbd` | "Salvar" nas Cancelas grava padrões errados (metal 90, papel 130) e a chave `vidro` (o vidro nunca aciona). A UI diz "Reinicie o backend", mas os ângulos valem na hora. | `ConfigGatesPanel.tsx` | Chave `glass`, padrões do backend (50/150/130/110), texto correto. |
| 3 | [x] `1ca641f` | A esteira religa sozinha: se o motor foi parado pela UI e há objeto na ROI, `motor_on` é chamado ao fim do acionamento. Sobra do design que parava a esteira na detecção. | `ecovision_local_modf.py` ("Finaliza processamento") | Remover o `motor_on`; deixar só `state.processing = False`. |
| 4 | [x] `1f08106` | Comando não numérico (ex.: `PING`) vira 0 com `toInt()` e move o servo a 0°. Não há posição inicial do servo no boot. | `firmware/src/main.cpp` | Validar dígitos e faixa 0..180 (também em `SERVO <n>`); `PING` → `PONG`; `motor.write(175)` no `setup()`. |
| 34 | [x] `1f08106` | `LED_PIN` (GPIO2, LED da placa) configurado e nunca usado. **Decisão: usar como LED de status.** | `firmware/src/main.cpp` | Aceso = motor ligado; pisca enquanto o servo segura a posição. Junto com o item 4. |
| 5 | [x] `9601534` | Câmera por URL não funciona pela UI: o campo é `type="number"` com `parseInt`, e salvar troca a URL por `NaN`. | `ConfigModelPanel.tsx` | Campo texto; converter para int só se for numérico. |
| 6 | [x] `f80bb71` | Se a câmera ou stream falha (URL errada, Wi-Fi), a thread YOLO morre e o servidor segue sem vídeo e sem aviso. | `process_yolo_stream` | Laço com `try/except` e nova tentativa a cada N s; logar o erro. |
| 11 | [x] `cbdf60a` | O seletor de modelo aponta para `yolov8{n,s,m,l,x}.pt`: `s` é COCO, `l`/`x` não existem, `best.pt` não aparece. | `ConfigModelPanel.tsx` | Lista fixa com os `.pt` TACO reais; selecionar o atual pelo `model_path`. |
| 13 | [x] `2cbf56f` | O badge "ESP32" mostra `COM8` fixo; "Câmera/YOLO: Ativo" reflete só o WebSocket. | `MonitorPanel.tsx`, backend (payload) | O backend envia `serial_port` (ou `null` em demo); câmera/YOLO ativos se chegaram frames recentes. |
| 28 | [x] `3875788` | `taco_to_material`: `carded blister pack` (existe no `best.pt`) não está mapeado; a chave `plastic glooves` é morta (o modelo usa `plastic gloves`). | `ecovision_local_modf.py` | Mapear explicitamente e remover a chave morta. |
| 29 | [x] `bc24683` | O FPS exibido é a média desde o início, não o FPS atual. | `process_yolo_stream` | Janela de 1 s. |
| 30 | [x] `05666aa` | `testes_serial.py` tem a porta fixa no código (mudança local não commitada: `/dev/ttyACM0`); a ajuda anuncia `PING` e ângulos antigos (60/90/120). **Decisão: ler a porta do `config.json`.** | `backend/testes_serial.py`, `backend/README.md` | Ler `serial_port`/`baud_rate` do `config.json`, com padrão se ele não existir; corrigir a ajuda. A mudança local deixa de ser necessária. |
| 35 | [x] `5b24934` | Com o backend offline, o "Salvar" fica desabilitado (item 18), mas os painéis de configuração continuam acessíveis e editáveis: o usuário mexe em valores que não pode salvar e que são sobrescritos pelo `get_config` quando o backend conecta. | `App.tsx`, `Sidebar.tsx`, `MonitorPanel.tsx` | Bloquear o acesso às páginas de configuração (Cancelas e Modelo) enquanto o backend estiver offline, em vez de desativar campo a campo: `App` usa o `connected` de `useStableWebSocket` (mesmo socket compartilhado) e passa para a `Sidebar`, que deixa esses itens desabilitados (com dica "Backend offline"). Se o backend cair com um painel de configuração aberto, voltar para o Monitor (com toast avisando). O Monitor continua acessível. O aviso de valores padrão e o `disabled` do "Salvar" do item 18 ficam como proteção extra. No `MonitorPanel`, desabilitar os botões de controle da esteira ("MOTOR ON"/"MOTOR OFF") quando não houver conexão serial com o ESP32 (`!connected || !serialPort`, ou seja, backend offline ou em modo demo). |

**Notas dos FC (sem hardware):** testados com um ESP32 falso num pty e as fotos de `legado/database/tcc-0CF` como câmera. Rajada de 60 comandos pelo WebSocket com a thread YOLO disparando: as 84 linhas chegaram íntegras. Confiança 0.35 → 0.8 em execução: daí em diante só detecções ≥ 0.8. Com um cliente que nunca lê, o outro manteve o FPS. Ctrl+C: `MOTOR OFF` enviado.

**Notas dos FS:** o item 4/34 exige regravar o ESP32. O item 28 deixou `carded blister pack` como `other` (decidido: fica assim). O `config.json` local foi migrado (`vidro` → `glass`, sem `type`).

## FC — Fix complexo (testar com hardware)

| # | Status | Problema | Correção |
|---|---|---|---|
| 9 | [~] `ed0e5c2`; falta o teste D | `conf` é fixado no início do stream; o slider de confiança não tem efeito. | Rodar o modelo com `conf` baixo e filtrar por `config['confidence']` no laço. |
| 10 | [~] `2701579`; falta o teste D | Serial sem lock (thread YOLO + handler asyncio); `read_reply` bloqueia o event loop e a inferência por até 1,5 s; uma resposta pode ser lida pelo leitor errado. Agravante: o firmware só responde `Servo movido` quando o servo começa o movimento (até 5 s por item na fila), então a resposta de um ângulo pode ser lida como a de um `MOTOR ON/OFF` seguinte. | Feito de outro jeito: `serial_lock` só na escrita (`send_line`) e ninguém espera resposta; a thread `read_serial_loop` registra tudo o que chega do ESP32. Sem `read_reply`, nada bloqueia, e o `to_thread` ficou desnecessário. |
| 12 | [~] `c519981`; falta o teste D | Broadcast sem controle de fila: cada frame agenda uma corrotina, e com cliente lento elas se acumulam. | Por cliente (`envios_pendentes`): pula o cliente cujo envio anterior ainda não terminou, sem atrasar os outros (um `gather` único travaria o vídeo de todos). Sem clientes, o quadro nem é codificado. |
| 32 | — | Limitação de projeto: o acionamento (5 s fixos) não acompanha a posição do objeto na esteira. | Rastreamento + atraso pela velocidade. Fora do escopo da refatoração. |

## P — Padronização

| # | Status | Item | Recomendação |
|---|---|---|---|
| 14 | [ ] | `print` em vez de `logging`. | `logging` com INFO/DEBUG. Serve de base para o registro de latência por etapa (RF09 da monografia). |
| 18 | [x] `026269d` | "Salvo localmente" grava no `localStorage` algo que ninguém lê. | Toast de erro. |
| 19 | [ ] | URL `ws://localhost:8765` repetida 3x; badge de status copiado em 3 painéis; lista de materiais duplicada no backend e no frontend; `MonitorPanel` adivinha o ícone por substring da classe em vez de usar `det.material`. | `src/config.ts` com URL e materiais; usar `det.material`. **Decisão: fazer agora só a URL, o badge e o `det.material`; a lista de materiais fica para a taxonomia hierárquica (seção 5.3.2), que vai substituí-la.** |
| 20 | [ ] | Bounding boxes desenhadas duas vezes (cv2 no backend + canvas no frontend); label com largura fixa de 200 px. | Manter só uma delas (preferência: frontend). |
| 21 | — | Identificadores misturam inglês e português. | Política: **não** renomear em massa; português no código novo. |
| 22 | [x] `53d7b51`, `7e54bfc` | Sem testes. | `backend/deteccao.py` (mapeamento, `deteccoes_do_quadro`, `angulo_a_disparar`) e 25 testes pytest em `backend/tests/`; `pytest` em `requirements-dev.txt`. |
| 31 | [ ] | `requirements.txt` só tem limites inferiores (`>=`); o ambiente atual usa Python 3.14. | Fixar versões testadas. Fazer antes de qualquer retreinamento (RNF07, reprodutibilidade). |
| 33 | [x] `b5246b4` | `vite` em `dependencies` e em `devDependencies` (6.3.5); `package.json` com a indentação torta do Figma. **Decisão: mover para `devDependencies`.** | Remover de `dependencies` e normalizar a indentação; verificar com `npm run build`. |

## D — Documentação

| # | Status | Item |
|---|---|---|
| 23 | [x] `b5246b4` | `backend/config.example.json` desatualizado: chave `corrugated carton` em vez de `glass`, campos não lidos (`websocket_port`, `frame_*`, `fps_target`), `confidence` 0.45. Atualizar ou apagar. |
| 24 | [x] `5198a85`, `1b7cfbd` | Mensagens que mandavam rodar `ecovision_local.py` e o "Reinicie o backend" após salvar ângulos. |
| 25 | [ ] | `docs/diagrams/` descreve classes inexistentes (`YOLOPipeline` etc.), login Google e `detection_queue`. Marcar como "arquitetura proposta (tese)" ou refazer. **Decisão: adiar; a arquitetura muda com os módulos novos (rastreamento, registro, anotação), então os diagramas são refeitos uma vez só, para o capítulo 6.** |
| 26 | [ ] | Sem registro do que mudou desde a tese. Criar `CHANGELOG.md` ou seção no README referenciando `tese-final`. |
| 27 | — | Regra contínua: atualizar "Limitações conhecidas" e `CLAUDE.md` a cada fix. `PROBLEMAS.md` reorganizado (`39b7b70`): só itens fora do código; P11 resolvido em `3f4f909`. |

---

## Testes de verificação dos FS

**Os blocos A a D serão executados de uma vez, antes do merge da branch na `main`.** Até lá, os itens FS e FC ficam sem confirmação em hardware.

Backup antes dos testes: `cp backend/config.json /tmp/config.bak.json`. Reinicie o backend a cada bloco (o Vite recarrega o frontend sozinho).

### A. Sem ESP32 (cabo desconectado) — backend + frontend

| # | Passo | Esperado |
|---|---|---|
| 13 | Subir o backend com o ESP32 desconectado | Log "Continuando sem serial"; Monitor → ESP32 = "Demo (sem serial)" |
| 6 | Subir com o app da câmera **fechado** | Log "Erro no stream da câmera ... Nova tentativa em 5 s", repetindo; WebSocket conecta normalmente |
| 6 | Abrir o app da câmera | Em ≤ 5 s: "Stream YOLO iniciado!" e vídeo no Monitor, **sem reiniciar o backend** |
| 13 | Fechar o app com o vídeo rodando | Em ~3 s: Câmera/YOLO = Inativo/Parado (o badge "Conectado" continua) |
| 29 | Observar o FPS com o vídeo rodando e ao tampar ou mexer na câmera | Valor varia a cada segundo, sem ficar "congelado" |
| 1 | Abrir o painel Modelo | Campos com os valores do `config.json`: URL da câmera, `/dev/ttyACM0`, `best.pt`, 35% (e não `COM8`/0/vazio) |
| 1 | Salvar sem alterar nada | `diff /tmp/config.bak.json backend/config.json` sem diferenças relevantes; sem chave `type` |
| 11 | Selecionar `150ep_best.pt` | Caminho muda para `../yolo_models/taco/150ep_best.pt`; digitar um caminho qualquer → seletor mostra "Outro arquivo" |
| 11 | Salvar `150ep_best`, reiniciar o backend | Log "Carregando modelo YOLO: ../yolo_models/taco/150ep_best.pt"; depois voltar para `best.pt` |
| 5 | Campo câmera: trocar para `0`, salvar | `config.json` com `"camera_index": 0` (número); voltar para a URL e salvar → string |
| 2 | Abrir Cancelas | 50 / 150 / 130 / 110, lidos do `config.json` |
| 2 | Mudar Vidro para 125, salvar | `config.json` com `"glass": 125`; toast "Os ângulos já estão valendo"; depois voltar para 130 |
| 18 | Abrir Modelo e Cancelas com o backend rodando e conferir os dois estados: com o backend conectado, "Salvar" habilitado; com o backend parado (antes do item 35, ou forçando `connected` falso), "Backend Offline", "Salvar" desabilitado e o aviso de valores padrão | O botão volta e os campos se preenchem quando o backend reconecta |
| 35 | Parar o backend com o frontend aberto | Itens Cancelas e Modelo desabilitados na barra lateral; com um deles aberto, parar o backend → volta para o Monitor com aviso; ao subir o backend, os itens voltam a ficar acessíveis. Monitor: botões da esteira desabilitados com o backend parado e no modo demo (ESP32 desconectado); habilitados com a serial ativa |

### B. Com ESP32, firmware antigo (ainda não regravado)

| # | Passo | Esperado |
|---|---|---|
| 13 | Subir o backend com o ESP32 conectado | Monitor → ESP32 = `/dev/ttyACM0` |
| 30 | Backend parado: `python backend/testes_serial.py` | "Conectado em /dev/ttyACM0"; `MOTOR ON`, `MOTOR OFF` e `90` funcionam. **Não** enviar `PING` |
| 3 | Backend rodando: parar a esteira pela UI, colocar um objeto parado **na faixa da ROI** e esperar > 5 s | O servo aciona uma vez e a esteira **continua parada** (antes ela religava) |
| 2 | Esteira ligada: passar uma garrafa de vidro | Log "Disparando: ... → glass → 130°"; servo a 130° (antes, o vidro não acionava depois de salvar pela UI) |
| — | Regressão: passar plástico, metal e papel | Ângulos 50 / 150 / 110 |
| — | Regressão: Ctrl+C no backend | Esteira desliga |

### C. Depois de regravar (`cd firmware && pio run -t upload`)

Testar com `python backend/testes_serial.py` (backend parado) ou `pio device monitor -b 115200`.

| # | Passo | Esperado |
|---|---|---|
| 4 | Reset/boot do ESP32 | Servo vai para 175°; LED apagado; "ESP32 pronto." |
| 4 | `PING` | `PONG`, servo parado |
| 4 | `abc`, `200`, `-5` | `ERR: comando invalido.`, servo parado |
| 4 | `SERVO 200`, `SERVO x` | `ERR: angulo invalido (0..180).` |
| 4 | `90`, depois `SERVO 45` | Move; LED pisca ~5 s; volta a 175°; o segundo executa depois do primeiro |
| 34 | `MOTOR ON` / `MOTOR OFF` | LED aceso / apagado junto com a esteira |
| 34 | `MOTOR ON` e depois `90` | LED pisca durante o servo e volta **aceso** no fim |
| 4 | Enviar 10 ângulos de uma vez (script abaixo) | `Servo movido para 10 graus` e um `ERR: fila do servo cheia.` (1 em execução + 8 na fila; o 10º é recusado) |
| — | Regressão: backend + UI com o firmware novo | Detecção aciona o servo; botões Ligar/Parar funcionam |

Script do teste de fila cheia (backend parado):

```bash
python - <<'PY'
import serial, time
s = serial.Serial('/dev/ttyACM0', 115200, timeout=1); time.sleep(2.5); s.reset_input_buffer()
s.write(b''.join(b'%d\n' % a for a in range(10, 110, 10))); time.sleep(1)
print(s.read_all().decode())
PY
```

### D. Fixes complexos (9, 10, 12), com ESP32 e câmera reais

Firmware novo gravado. Backend + frontend rodando, esteira ligada. Acompanhar o log do backend.

| # | Passo | Esperado |
|---|---|---|
| 10 | Subir o backend | `ESP32: OK MOTOR ON` no log, vindo da thread de leitura; a esteira liga |
| 10 | Passar um objeto pela ROI | `Disparando...` e, logo depois, `ESP32: Servo movido para N graus`; o FPS no Monitor **não** cai no disparo (antes congelava até 1,5 s) |
| 10 | Passar 3 objetos seguidos e, enquanto o servo trabalha, clicar MOTOR OFF / MOTOR ON | A esteira obedece na hora; cada `OK MOTOR ...` e cada `Servo movido` aparece uma vez, sem `ERR: comando invalido.` (seria sinal de linhas misturadas) |
| 10 | Monitor: "Testar" em Cancelas várias vezes rápido com a esteira detectando | Nenhum `ERR: comando invalido.`; com mais de 9 ângulos na fila, `ERR: fila do servo cheia.` é o esperado |
| 10 | Desconectar o cabo USB com o backend rodando | Log `[DEMO] Falha ao ler da serial` (ou de envio); Monitor → ESP32 = "Demo (sem serial)"; vídeo continua |
| 10 | Ctrl+C no backend | A esteira desliga; sem traceback da thread de leitura |
| 9 | Painel Modelo: confiança em 90%, Salvar | Toast "A confiança já vale..."; no Monitor, as caixas abaixo de 90% somem em ~1 s, **sem reiniciar** |
| 9 | Com 90%, passar um objeto que antes era detectado com ~50% | Não aciona o servo |
| 9 | Voltar a 35%, Salvar | As caixas voltam; o objeto aciona de novo |
| 9 | Comparar o FPS com 35% e com 10% | Parecido (o modelo já roda em 0.1); se cair muito, subir `CONF_MINIMA_MODELO` |
| 12 | Abrir o frontend em duas abas e, numa delas, pausar o JS (DevTools → Sources → pausar) por ~30 s | A outra aba segue com vídeo fluido; ao despausar, a aba pausada volta a receber; a memória do backend (`top`/Gerenciador de Tarefas) não sobe continuamente |
| 12 | Câmera por URL do celular (Wi-Fi) com o frontend aberto | Vídeo sem atraso crescente: mexer a mão diante da câmera aparece no Monitor com atraso constante |
| 12 | Fechar todas as abas | O backend segue disparando o servo normalmente (a detecção não depende de cliente conectado) |

