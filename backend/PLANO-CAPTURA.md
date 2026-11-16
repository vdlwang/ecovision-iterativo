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
| 4 | [x] `40e76d5` | **`importar.py`: conferência de Δ.** Lê o horário do EXIF antes de regravar (a regravação o descarta); sem fuso, hora local. Coluna `imagens.capturada_em` (pode ser nula; esquema v7, sem migração). `--janela` (Δ em segundos, padrão 10; também no `anotadores.yaml`): em ordem de horário, cada imagem nova com outra a menos de Δ (no banco ou no próprio lote) herda o conjunto dela e é listada no relatório; vizinhas em conjuntos diferentes geram aviso; sem horário, sorteio por imagem como hoje | pytest com EXIF sintético; importar os 4 cenários de `legado/database` (mesmas cenas, segundos de diferença) e conferir que cada cena cai num conjunto só |
| 5 | [x] | **Documentação**: `backend/README.md` (bloco `captura`, `--capturar`), `anotacao/README.md` (`--janela`, `capturada_em`), `OBJETIVO.md` (T4), `REFATORACAO.md` (37, 38, 40), `CHANGELOG.md`, `CLAUDE.md` | — |
| 6a | [ ] | **Câmera aberta pelo backend** (antes da ida à esteira, decisão 3 revista): o backend abre a `cv2.VideoCapture`, aplica o bloco `camera` do `config.json` (resolução, formato, exposição, balanço de branco, foco), confere o que a câmera aceitou e passa os quadros ao YOLO com `imgsz` explícito; tudo registrado no `captura.jsonl`. Sem o bloco, comporta-se como hoje. `ajustar_camera.py` para a calibração. Detalhes em [Etapa 6](#etapa-6-câmera-configurada) | pytest de `camera.py` com câmera falsa; backend com a webcam local e com vídeo |
| 6b | [ ] | **Calibração na esteira** (primeiro passo da ida, antes de qualquer captura): escolher resolução, exposição, balanço de branco e foco com o `ajustar_camera.py` e fixá-los no `config.json` | quadros de amostra; valores lidos de volta iguais aos pedidos |
| 7 | [ ] | **Na esteira**: medir a travessia (cronometrar um objeto cruzando o campo da câmera), ajustar Δ com folga, sessão-piloto dos três ramos da captura, sessão de captura e importação com `--janela` sem nenhuma imagem acusada. Variar os objetos e não repassar o mesmo de propósito (decisão 19 do `OBJETIVO.md`). Roteiro em [Etapa 7](#etapa-7-sessão-na-esteira) | sessão real |

Commits: um para a etapa 1; um para 2 e 3; um para 4; a documentação vai junto de cada etapa.

**Conferido (etapas 2 e 3, 2026-11-15)**: 16 testes em `backend/tests/test_captura.py`; o backend rodou com um vídeo de 8 fotos de `tcc-0CF` como câmera e o ESP32 simulado num pty, com `intervalo_s` 1 e `travessia_s` 0,5: com o motor ligado, gravou depois da travessia; com o motor desligado pela UI, só quando a foto do vídeo mudava (diferença de 22 a 82, contra o limiar 10); 6 quadros, nenhum descartado, EXIF e `captura.jsonl` certos; um `config.json` sem `class_to_angle` e sem `captura` rodou com os padrões. A resolução gravada é a que o Ultralytics entrega (a do vídeo, 960×720).

**Conferido (etapa 4, 2026-11-16)**: 5 testes novos em `anotacao/tests/test_importar.py`. Dois desvios do plano: (1) sem EXIF, o horário vem do nome no padrão das câmeras de celular (`20250503_140329.jpg`, hora local), porque as fotos de `legado/database` perderam o EXIF na exportação e a verificação não rodaria; (2) o `--janela` da pipeline é opção de linha de comando, como as outras da importação, e não fica no `anotadores.yaml`. Os 4 cenários de `legado/database` (88 fotos), importados um lote por cenário, não cumprem "cada cena num conjunto só" com Δ = 10 s: as fotos de celular de uma cena às vezes distam mais de 10 s entre cenários.

| Δ | grupos | de 1 imagem | nos dois conjuntos |
|---|---|---|---|
| 10 s | 42 | 15 | 2 |
| 30 s | 26 | 5 | 0 |
| 60 s | 21 | 3 | 1 |

Os grupos nos dois conjuntos aparecem quando um lote posterior liga imagens já importadas em conjuntos diferentes; o importar.py avisa, mas o conjunto gravado não muda. Na captura do backend (uma sessão contínua, importada como um lote) não deve ocorrer; as bases antigas, de celular, são conferidas à mão.

## Etapa 6: câmera configurada

Planejada em 2026-11-16. Objetivo: os quadros da operação e os da captura saem da câmera numa condição fixa e registrada, a mesma em todas as sessões, desde a primeira. A exposição e o balanço de branco automáticos mudam a imagem conforme o que está na esteira (um objeto escuro clareia o fundo), o que muda a entrada do YOLO quadro a quadro e faz a captura com o motor desligado disparar sem nada ter mudado na cena.

### 6a. Código (antes de ir)

**Bloco `camera` no `config.json`** (completado pelos padrões em `load_config()`, como o `captura`; `camera_index` continua no nível de cima, porque o frontend o edita). `null` = não mexer (padrão do driver), então um `config.json` sem o bloco se comporta como hoje:

| Campo | Padrão | Uso |
|---|---|---|
| `largura`, `altura` | `null` | Resolução pedida (ex.: 1280×720) |
| `fourcc` | `null` | Formato do stream, ex.: `"MJPG"`. Em USB 2, o YUYV não passa de ~5–10 fps em 720p ou acima; o MJPG passa de 30 |
| `fps` | `null` | Taxa pedida |
| `exposicao` | `null` | `null` = automática; um número = manual, na unidade do backend do OpenCV (DSHOW no Windows: log2 de segundos, ex.: `-6` ≈ 1/64 s; V4L2 no Linux: `exposure_time_absolute`, em 100 µs) |
| `temperatura_cor` | `null` | `null` = balanço de branco automático; em kelvin = manual (ex.: 4500) |
| `foco` | `null` | `null` = autofoco; um número = foco manual fixo (a distância até a esteira não muda, e o autofoco "caçando" borra quadros) |
| `ganho` | `null` | Ganho manual, se a exposição manual deixar a imagem escura |
| `imgsz` | `640` | Passado ao YOLO de forma explícita (o `best.pt` treinou com 640) |

**`backend/camera.py`** (lógica separada do laço, como `captura.py`):
- `abrir(indice_ou_url, cfg)`: abre a `VideoCapture` com o backend explícito (`CAP_DSHOW` no Windows, `CAP_V4L2` no Linux), aplica as propriedades na ordem certa (formato antes da resolução; desligar o automático antes de pôr o valor manual) e devolve a captura e um relatório.
- `propriedades(cfg, backend)`: traduz o bloco em pares (propriedade OpenCV, valor). O liga/desliga do automático muda de valor conforme o backend (V4L2: `CAP_PROP_AUTO_EXPOSURE` 1 = manual, 3 = automático; DSHOW: 0,25/0,75). Função pura, com pytest.
- `conferir(pedido, lido)`: lê de volta cada propriedade e lista as divergências. A câmera pode ignorar um valor em silêncio ou arredondar (pedir 1366×768 e receber 1280×720). Uma divergência sai em WARNING no log e vai para o `captura.jsonl`, sem derrubar o backend.
- URL (stream de IP Webcam): nenhuma propriedade se aplica. Com o bloco preenchido, o backend avisa e segue.
- As propriedades são reaplicadas a cada reabertura (reconexão), porque algumas webcams voltam ao padrão.

**Leitura em thread própria** (`camera`): lê continuamente e guarda só o quadro mais recente. É o que o `LoadStreams` do Ultralytics faz hoje; sem isso, o buffer do OpenCV acumula quadros, e o YOLO veria a esteira com atraso, o que atrasa o servo. O laço do YOLO pega o último quadro e chama `model(quadro, conf=..., imgsz=..., verbose=False)`. Se a leitura falhar, reabre depois de `CAMERA_RETRY_SECONDS`, como hoje. O resto do laço (detecções, disparo, captura, WebSocket) não muda.

**Registro**: a linha `sessao` do `captura.jsonl` ganha o bloco `camera` pedido, os valores lidos de volta, o backend do OpenCV e o `imgsz`. O log de INFO da abertura diz a resolução, o formato e a taxa efetivos.

**`backend/ajustar_camera.py`** (ferramenta de calibração, com o backend parado):
- lista as resoluções e formatos aceitos (no Linux, por `v4l2-ctl --list-formats-ext`, se existir; senão pede uma lista comum, de 640×480 a 1920×1080, e lê de volta) e mede o fps efetivo de cada uma, em 3 s de leitura;
- `--varrer exposicao -8 -4` (ou `temperatura_cor`, `foco`): grava um quadro por valor em `capturas/ajuste/<horário>/`, com o valor no nome, para comparar lado a lado;
- aplica o bloco `camera` do `config.json`, mostra os valores lidos de volta e grava um quadro de amostra.

**Verificação**:
- pytest de `camera.py` com uma `VideoCapture` falsa: ordem das propriedades, tradução por backend, divergência acusada, URL sem propriedades;
- o backend com a webcam deste computador (Linux, V4L2), com e sem o bloco `camera`: vídeo no Monitor, valores lidos de volta e `captura.jsonl`; com um vídeo como `camera_index`, a captura continua igual à da etapa 3;
- o tempo do quadro até o disparo não pode piorar: comparar o fps do Monitor antes e depois na mesma câmera.

**Pendência**: o sistema operacional da máquina da esteira. As unidades de exposição e de autofoco mudam entre DSHOW e V4L2, e a equipe desenvolveu no Windows. Testar a 6a no sistema da máquina da esteira, ou levar as duas traduções testadas.

### 6b. Calibração (primeiro passo na esteira)

Com a esteira montada, a iluminação que será usada sempre e objetos dos quatro materiais no campo:

1. **Iluminação**: preferir luz artificial e fechar cortinas. Com exposição manual, a luz do dia variando muda o brilho entre sessões. Se não der para controlar, anotar a condição de cada sessão.
2. **Resolução e formato**: a maior com MJPG que mantém o fps do Monitor perto do de hoje (o YOLO é o gargalo; decodificar 1080p custa CPU). Provável 1280×720.
3. **Foco**: varrer `foco` e escolher o quadro mais nítido sobre a lona.
4. **Exposição**: varrer e escolher a mais curta (menos borrão com a esteira andando) que não escurece os objetos escuros. Se escurecer, subir o `ganho` antes de alongar a exposição. Conferir com objetos brilhantes (lata, vidro): sem estourar.
5. **Balanço de branco**: varrer `temperatura_cor` e escolher o que deixa a lona e um papel branco neutros.
6. Gravar os valores no `config.json` e rodar `ajustar_camera.py` uma última vez: os valores lidos de volta iguais aos pedidos.
7. Rodar o backend sem captura e conferir as detecções do `best.pt` no Monitor. Se piorarem muito em relação ao automático, rever a exposição.

Os valores escolhidos valem para a operação e para a captura de todas as sessões; mudá-los depois cria uma condição nova, registrada no `captura.jsonl` de cada sessão. O `config.example.json` e os padrões não mudam: são de cada câmera.

## Etapa 7: sessão na esteira

Roteiro de 2026-11-16. Começa depois da 6b, com a câmera já fixada.

**Antes de ir**:
- Recomendado: corrigir os itens 36 e 39 do `REFATORACAO.md`. "Testar Conexão Serial" sempre termina em `MOTOR OFF`, e um clique na sessão para a esteira sem aviso, com a captura passando ao ramo de motor desligado. Um cabo USB mexido deixa o backend em modo demo até reiniciar.
- Na máquina da esteira: venv com `backend/requirements.txt`, `python -m pytest backend/tests` passando, `python backend/test_connection.py` achando a câmera e a porta, e `serial_port`/`camera_index` certos no `config.json`.
- Levar objetos dos quatro materiais, os mais variados possível (cada um passa uma vez, decisão 19), um cronômetro ou o celular para filmar, e onde anotar.

**1. Sistema montado** (`./run.sh --debug=true`, sem captura): vídeo no Monitor; `serial_port` diferente de `null`; `MOTOR ON`/`MOTOR OFF` com o LED acompanhando; um ângulo move o servo. Anotar o fps.

**2. Travessia e Δ**: com o motor ligado (PWM fixo 255), cronometrar do instante em que um objeto aparece no quadro até a borda de trás sair, 5 vezes, com objetos de tamanhos diferentes (ou filmar a tela e contar quadros). `travessia_s` = a maior medida (é a espera depois de ligar o motor). `intervalo_s` (Δ) ≈ 1,5 × a travessia máxima, com folga para objetos que escorregam ou travam. Anotar também a velocidade (comprimento do campo ÷ tempo), útil para o T15.

**3. Sessão-piloto** (~5 min, `./run.sh --capturar=true`, com os valores medidos). O log deve dizer `Captura ativa: a cada X s no mínimo (travessia Y s)`. Exercitar os três ramos:

| Situação | Esperado |
|---|---|
| Ligar o motor | Nada gravado durante `travessia_s`; depois, um quadro a cada Δ |
| Desligar o motor, cena parada | Nada gravado (diferença abaixo de `diferenca_minima`) |
| Motor desligado, trocar um objeto à mão | Um quadro, se já passou Δ |

Conferir em `backend/capturas/<sessão>/`: nome e EXIF com o horário; `captura.jsonl` com a sessão (incluindo o bloco `camera` lido de volta) e uma linha por quadro, com `motor_ligado` coerente; nenhum aviso de quadro descartado. Ajustar `diferenca_minima` se disparar com a cena parada ou não disparar ao trocar um objeto. Definir a região de interesse da anotação (`--regiao`, normalizada) olhando 2 ou 3 quadros. Ela é outra coisa que a faixa de acionamento `roi_y_min`/`roi_y_max`.

**4. Sessão de captura** (20 a 30 min, motor ligado a maior parte do tempo): cada objeto passa uma vez; variar quantos aparecem por quadro (um, vários, sobrepostos, nenhum), a posição na largura e a orientação; incluir o que o `best.pt` erra; se possível, um trecho com o motor desligado e objetos postos à mão. Com Δ = 6 s, 30 min dão ~300 quadros, ~30 de teste. Se faltar objeto, encurtar: menos quadros sem repetição valem mais.

**5. Importação**:

```bash
python anotacao/importar.py backend/capturas/<sessão> \
    --lote esteira-<data> --janela <Δ> --regiao X1 Y1 X2 Y2
```

Critério: **nenhuma imagem acusada**, com `--janela` igual ao `intervalo_s`. O espaçamento usa `time.monotonic()`, e o EXIF, o relógio do sistema. Se houver acusação, conferir no `captura.jsonl` se o intervalo foi mesmo menor que Δ (seria bug) ou se o relógio saltou (NTP), e registrar. Conferir também a proporção do teste (~10%).

**6. Fechar**: etapa 7 `[x]` com um bloco "Conferido" (travessia medida, Δ, `travessia_s` e `diferenca_minima` adotados, câmera, fps, quadros por ramo, acusadas, treino/teste); padrões do `PADROES_CAPTURA` e `backend/README.md` se mudarem; `OBJETIVO.md` (T4) e `CHANGELOG.md`. Depois, refazer a linha de base dos anotadores com quadros da esteira (os limiares foram escolhidos em fotos de celular; `OBJETIVO.md`, "Resolução e origem das imagens").

## Decisões (2026-11-15)

| # | Questão | Decisão |
|---|---|---|
| 1 | Reset do ESP32: reenviar o último estado do motor ou marcá-lo desligado? | **Marcar desligado.** O ESP32 volta com o motor parado; a esteira não religa sozinha, e o operador a liga pela UI. |
| 2 | Δ antes de medir a travessia? | **10 s**, no `config.json` e no `--janela`; ajustado na esteira (etapa 7). |
| 3 | ~~Resolução e exposição agora?~~ | ~~**Depois** da primeira ida à esteira (etapa 6).~~ **Revista (2026-11-16)**: o código antes da ida (6a), a escolha dos valores no começo dela (6b), antes de qualquer captura. Assim todas as sessões saem na mesma condição de câmera, e não sobra um lote com a exposição automática para decidir se entra na base. |

## Verificação geral

```bash
.venv/bin/python -m pytest backend/tests anotacao/tests
.venv/bin/python -m py_compile backend/*.py
```

Mais o teste do backend sem hardware (etapa 3) e a sessão na esteira (etapa 7).
