# Plano — captura na esteira (T4)

Plano da tarefa T4 do [`OBJETIVO.md`](../OBJETIVO.md): o backend grava quadros da esteira para a anotação, espaçados no tempo, e a importação confere pelo horário de captura que duas imagens não são próximas demais. As decisões de fundo estão no `OBJETIVO.md` ("Captura sem duplicatas e vazamento" e decisões 7 e 19); este arquivo diz como implementá-las. Escrito em 2026-11-15.

**Status**: `[ ]` pendente · `[x]` feito (com hash) · `[~]` parcial

## Ponto de partida

- **O laço do YOLO já tem o quadro original** (`result.orig_img` em `run_yolo_stream`): é onde a captura entra, sem abrir a câmera duas vezes.
- **A resolução é a padrão do driver**: o Ultralytics abre a câmera só pelo índice, sem largura, altura nem exposição. Fixá-las exige que o backend abra a `cv2.VideoCapture` e passe os quadros ao modelo, o que reescreve o laço e a reconexão; fica para a etapa 6.
- **O estado do motor não era confiável** (itens 37 e 38 do `REFATORACAO.md`): começava ligado, mudava mesmo sem o comando chegar ao ESP32, e um reset do ESP32 não era percebido. A captura depende dele, então vira pré-requisito.
- **Gravar no laço atrasaria a inferência**: um JPEG de 1080p em qualidade 95 leva dezenas de milissegundos. A gravação vai para uma thread própria, com fila curta que descarta quando cheia.

## Etapas

| # | Status | Entrega | Verificação |
|---|---|---|---|
| 1 | [x] `403c5e1` | **Estado do motor confiável** (itens 37 e 38). `backend/motor.py` (lógica pura): o estado começa desligado e só muda quando o comando foi enviado à serial; ao ler `ESP32 pronto.` (reset do ESP32), marca desligado (decisão 1, abaixo). Guarda desde quando o motor está ligado, para a etapa 2 | pytest de `motor.py` |
| 2 | [x] `5fe875b` | **`backend/captura.py`** (lógica pura, como o `deteccao.py`): `deve_capturar(...)`: com o motor ligado, passou o intervalo Δ desde a última captura e uma travessia desde que o motor ligou; com o motor desligado ou em modo demo, a diferença para o último quadro gravado passa de `diferenca_minima` e passou Δ. `diferenca_quadros(a, b)`: diferença absoluta média entre versões pequenas, em cinza. Espaçamento por `time.monotonic()`; o horário gravado, pelo relógio do sistema | pytest com quadros e tempos sintéticos |
| 3 | [x] `5fe875b` | **Integração no backend.** Bloco `captura` no `config.json`: `ativa` (padrão `false`), `pasta`, `intervalo_s` (Δ, padrão 10), `travessia_s`, `diferenca_minima`; o `load_config()` completa as chaves que faltam (resolve o item 40). Liga por `--capturar=true` ou por `ativa`. Cada execução grava em `capturas/<data-hora UTC>/` (gitignored): JPEG 95 por Pillow com o horário no EXIF (`DateTimeOriginal`, `SubSecTimeOriginal`, `OffsetTimeOriginal`) e no nome, e `captura.jsonl` com a configuração da sessão e uma linha por quadro (horário, motor, resolução, detecções). Thread de gravação com fila curta. Pillow fixado no `requirements.txt` | pytest; backend em modo demo com vídeo ou pasta como câmera: arquivos, EXIF e espaçamento |
| 4 | [ ] | **`importar.py`: conferência de Δ.** Lê o horário do EXIF antes de regravar (a regravação o descarta); sem fuso, hora local. Coluna `imagens.capturada_em` (pode ser nula; esquema v7, sem migração). `--janela` (Δ em segundos, padrão 10; também no `anotadores.yaml`): em ordem de horário, cada imagem nova com outra a menos de Δ (no banco ou no próprio lote) herda o conjunto dela e é listada no relatório; vizinhas em conjuntos diferentes geram aviso; sem horário, sorteio por imagem como hoje | pytest com EXIF sintético; importar os 4 cenários de `legado/database` (mesmas cenas, segundos de diferença) e conferir que cada cena cai num conjunto só |
| 5 | [ ] | **Documentação**: `backend/README.md` (bloco `captura`, `--capturar`), `anotacao/README.md` (`--janela`, `capturada_em`), `OBJETIVO.md` (T4), `REFATORACAO.md` (37, 38, 40), `CHANGELOG.md`, `CLAUDE.md` | — |
| 6 | [ ] | **Câmera aberta pelo backend** (depois da primeira ida à esteira, decisão 3): largura, altura, exposição e balanço de branco fixos no `config.json`, `imgsz` explícito, registrados no `captura.jsonl` | teste com a webcam da esteira |
| 7 | [ ] | **Na esteira**: medir a travessia (cronometrar um objeto cruzando o campo da câmera), ajustar Δ com folga, sessão curta de captura e importação com `--janela` sem nenhuma imagem acusada. Variar os objetos e não repassar o mesmo de propósito (decisão 19 do `OBJETIVO.md`) | sessão real |

Commits: um para a etapa 1; um para 2 e 3; um para 4; a documentação vai junto de cada etapa.

**Conferido (etapas 2 e 3, 2026-11-15)**: 16 testes em `backend/tests/test_captura.py`; o backend rodou com um vídeo de 8 fotos de `tcc-0CF` como câmera e o ESP32 simulado num pty, com `intervalo_s` 1 e `travessia_s` 0,5: com o motor ligado, gravou depois da travessia; com o motor desligado pela UI, só quando a foto do vídeo mudava (diferença de 22 a 82, contra o limiar 10); 6 quadros, nenhum descartado, EXIF e `captura.jsonl` certos; um `config.json` sem `class_to_angle` e sem `captura` rodou com os padrões. A resolução gravada é a que o Ultralytics entrega (a do vídeo, 960×720).

## Decisões (2026-11-15)

| # | Questão | Decisão |
|---|---|---|
| 1 | Reset do ESP32: reenviar o último estado do motor ou marcá-lo desligado? | **Marcar desligado.** O ESP32 volta com o motor parado; a esteira não religa sozinha, e o operador a liga pela UI. |
| 2 | Δ antes de medir a travessia? | **10 s**, no `config.json` e no `--janela`; ajustado na esteira (etapa 7). |
| 3 | Resolução e exposição agora? | **Depois** da primeira ida à esteira (etapa 6). |

## Verificação geral

```bash
.venv/bin/python -m pytest backend/tests anotacao/tests
.venv/bin/python -m py_compile backend/*.py
```

Mais o teste do backend sem hardware (etapa 3) e a sessão na esteira (etapa 7).
