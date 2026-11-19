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
| 6a | [x] `6316da1` | **Câmera aberta pelo backend** (antes da ida à esteira, decisão 3 revista): o backend abre a `cv2.VideoCapture`, aplica o bloco `camera` do `config.json` (resolução, formato, exposição, balanço de branco, foco), confere o que a câmera aceitou e passa os quadros ao YOLO com `imgsz` explícito; tudo registrado no `captura.jsonl`. Sem o bloco, comporta-se como hoje. `ajustar_camera.py` para a calibração. Detalhes em [Etapa 6](#etapa-6-câmera-configurada) | pytest de `camera.py` com câmera falsa; backend com a webcam local e com vídeo |
| 6b | [~] | **Calibração na esteira** (primeiro passo da ida, antes de qualquer captura): escolher resolução, exposição, balanço de branco e foco com o `ajustar_camera.py` e fixá-los no `config.json`. **Revista em 2026-11-18**: sem controle de luz por ora, só formato, resolução, fps e controles de imagem fixados; exposição, ganho, balanço de branco e foco no automático, e a captura com o motor desligado compara quadros com o brilho igualado. Fixar a exposição é [melhoria futura](#melhoria-futura-luz-controlada-e-exposição-fixa) | quadros de amostra; valores lidos de volta iguais aos pedidos |
| 6c | [x] | **Captura por objeto novo** (2026-11-18): com o motor ligado, o temporizador dá lugar a uma captura `atraso_s` depois de um objeto entrar na lona vazia, com Δ desde a última; o objeto vem da diferença para a lona (`OcupacaoLona`), não do YOLO. Motivo e números no `OBJETIVO.md` ("Captura sem duplicatas e vazamento", revista) | pytest com quadros sintéticos; as fotos da sessão de 2026-11-18 em sequência: os 6 objetos capturados, nenhuma lona vazia |
| 7 | [ ] | **Na esteira**: medir a travessia (cronometrar um objeto cruzando o campo da câmera), ajustar Δ com folga, sessão-piloto dos três ramos da captura, sessão de captura e importação com `--janela` sem nenhuma imagem acusada. Variar os objetos e não repassar o mesmo de propósito (decisão 19 do `OBJETIVO.md`). Roteiro em [Etapa 7](#etapa-7-sessão-na-esteira) | sessão real |

Commits: um para a etapa 1; um para 2 e 3; um para 4; um para 6a; a documentação vai junto de cada etapa.

**Conferido (etapas 2 e 3, 2026-11-15)**: 16 testes em `backend/tests/test_captura.py`; o backend rodou com um vídeo de 8 fotos de `tcc-0CF` como câmera e o ESP32 simulado num pty, com `intervalo_s` 1 e `travessia_s` 0,5: com o motor ligado, gravou depois da travessia; com o motor desligado pela UI, só quando a foto do vídeo mudava (diferença de 22 a 82, contra o limiar 10); 6 quadros, nenhum descartado, EXIF e `captura.jsonl` certos; um `config.json` sem `class_to_angle` e sem `captura` rodou com os padrões. A resolução gravada é a que o Ultralytics entrega (a do vídeo, 960×720).

**Conferido (etapa 4, 2026-11-16)**: 5 testes novos em `anotacao/tests/test_importar.py`. Dois desvios do plano: (1) sem EXIF, o horário vem do nome no padrão das câmeras de celular (`20250503_140329.jpg`, hora local), porque as fotos de `legado/database` perderam o EXIF na exportação e a verificação não rodaria; (2) o `--janela` da pipeline é opção de linha de comando, como as outras da importação, e não fica no `anotadores.yaml`. Os 4 cenários de `legado/database` (88 fotos), importados um lote por cenário, não cumprem "cada cena num conjunto só" com Δ = 10 s: as fotos de celular de uma cena às vezes distam mais de 10 s entre cenários.

| Δ | grupos | de 1 imagem | nos dois conjuntos |
|---|---|---|---|
| 10 s | 42 | 15 | 2 |
| 30 s | 26 | 5 | 0 |
| 60 s | 21 | 3 | 1 |

Os grupos nos dois conjuntos aparecem quando um lote posterior liga imagens já importadas em conjuntos diferentes; o importar.py avisa, mas o conjunto gravado não muda. Na captura do backend (uma sessão contínua, importada como um lote) não deve ocorrer; as bases antigas, de celular, são conferidas à mão.

**Conferido (etapa 6a, 2026-11-16)**, na máquina da esteira (Fedora 43, OpenCV 5.0 com V4L2), com a câmera da esteira (DV20 USB) conectada mas ainda não apontada para a esteira:

- **A câmera**: `/dev/video2` (o `/dev/video3` é o nó de metadados; o `camera_index: 3` do `config.json` não abre). Sem configuração, abre em YUYV 640×480 a 10 fps. Aceita MJPG 640×480 e 1280×720 (30 fps anunciados) e YUYV 640×480 e 320×240. Controles: exposição automática ou manual (`exposure_time_absolute` de 80 a 100000), ganho 1–7, temperatura de cor 0–6500 só manual (sem balanço automático), sem foco. Contraste, saturação e nitidez são lidos como 0 (padrões 256, 256 e 128), mas a imagem sai em cores: leitura errada do driver.
- **OpenCV 5 com V4L2**: passa os valores sem conversão (`AUTO_EXPOSURE` 1 = manual, 3 = automático; `CAP_PROP_EXPOSURE` = `exposure_time_absolute`); os valores ficam no driver depois de fechar (confirmado: daí os automáticos postos de forma explícita).
- **fps**: 12 em qualquer formato e resolução, também pelo `v4l2-ctl --stream-mmap` direto, sem OpenCV: limite da câmera nesta luz, não do código. Com exposição manual longa cai mais (6 fps em 80000), então a unidade não é a de 100 µs da especificação V4L2. Medir de novo na esteira, com a iluminação dela (6b).
- **Backend** em modo demo, cliente WebSocket contando quadros: o código anterior (Ultralytics) a 12–13 fps; o novo, sem o bloco `camera`, a 12 fps (YUYV 640×480, como antes); com MJPG 1280×720, 12 fps. A captura gravou em 1280×720, com o relatório da câmera na linha de sessão (pedido, lido, sem divergências). O segundo quadro, com a cena parada e o motor desligado, diferiu 14,6 do primeiro: a exposição automática assentando logo depois de abrir, o que a exposição manual da 6b evita.
- **Vídeo como câmera** (8 fotos de `tcc-0CF`, 2 fps, captura com `intervalo_s` 1): lido no ritmo do vídeo, uma captura por foto, fim do vídeo e reabertura com a linha `camera` no `captura.jsonl`. Esse teste achou um erro (o `tipo` do relatório sobrescrevia o da linha), corrigido antes do commit.
- **`ajustar_camera.py`**: `--listar` e `--varrer exposicao` rodaram na DV20; os valores que mudaram no driver foram devolvidos aos de antes.
- 20 testes em `backend/tests/test_camera.py`. Não testado: Windows (DSHOW), stream por URL com o leitor novo.

**Calibração em andamento (6b, 2026-11-16)**, câmera apontada para a esteira, com objetos coloridos (caixa de papel branco, azul e vermelho, faca amarela, embalagem de café):

- **Campo de visão**: 640×480 e 1280×720 mostram o mesmo trecho da esteira (os objetos ocupam as mesmas frações do quadro): o sensor é 16:9, e o 640×480 o espreme na horizontal. A câmera pega um trecho curto da esteira por estar perto e ter campo estreito; resolução não muda isso. Pendente, físico: subir a câmera ou trocar a lente, e o foco (a imagem está desfocada, e a DV20 não tem foco por software; conferir se a lente tem anel).
- **Cor**: a DV20 liga com contraste, saturação e nitidez internos que dão uma imagem azulada, enquanto o driver lê 0 (0 posto de verdade deixa a imagem preta). Os controles de imagem entraram no bloco `camera` (brilho, contraste, saturação, nitidez, gama), aplicados a cada abertura. Escolhidos numa grade de contraste × saturação × gama: 0, 256, 384, 128, 20 (a 450 o vermelho estoura). A `temperatura_cor` é aceita e lida de volta, mas não muda a imagem (3500 a 6500, o mesmo quadro): o balanço de branco desta câmera não é ajustável.
- **Adotado no `config.json` da máquina**: MJPG 1280×720, 30 fps pedidos (12 medidos), os controles de imagem acima, exposição ainda automática.
- **Câmera reposicionada** (mais alta): o quadro pega a largura toda da esteira e o foco ficou bom; as bordas de cima e de baixo pegam o que está fora da lona (cabos, mesa), o que a região de interesse da anotação (`--regiao`) corta.
- **Exposição**: varrida com a esteira andando, na luz ambiente da sala. A unidade da DV20 é de ~2 µs (60000 derruba o fps para 8, 80000 para 6). Para a lona ficar tão clara quanto no automático, são precisos ~60000 (~120 ms); com 15000 (~30 ms) a imagem sai quase preta, e o ganho não faz efeito (54 de brilho com ganho 4 e com 7). Uma exposição de ~100 ms com a esteira andando borra os objetos. No automático, os brancos estouram (10% do quadro a 250+ com objetos brancos), porque a lona escura domina a média. **Conclusão**: falta luz; a exposição manual curta só serve com iluminação forte sobre a esteira. Fica no automático até lá.
- **A DV20 é fraca para o trabalho**: 12 fps em qualquer resolução, ganho e temperatura de cor que não fazem efeito, sem foco ajustável, valores internos que o driver informa errado. Recomendado trocá-la por uma webcam UVC com exposição, balanço de branco e foco manuais funcionando e 30 fps reais em 720p, e iluminar a esteira (o que vale com qualquer câmera).
- **Comparação com o celular** (mesma cena, um pacote de café colorido sobre a lona, luz ambiente): a foto do celular sem flash registra o pacote inteiro com as cores certas e a lona com textura; a DV20 estoura a metade colorida do pacote (7% do quadro a 250+) e deixa a lona cinza-esverdeada. A luz da sala basta para um sensor bom; o limite da DV20 é a faixa dinâmica: com a lona preta e um objeto claro juntos, a exposição automática clareia pela lona e estoura o objeto. Ressalva: a foto do celular é parada, com exposição longa e várias exposições somadas; a comparação justa é um vídeo do celular a 30 fps. A foto com flash mostra o efeito de uma luz direta e forte: tudo nítido e uniforme.
- **Montagem**: o suporte e a própria câmera fazem sombra na lona quando a luz vem de cima, perto dela; iluminar dos dois lados da esteira, em ângulo. A colcha estampada ao lado da esteira entra na faixa de baixo do quadro, e os cabos na de cima: a região de interesse da anotação os corta, mas na operação a estampa pode gerar detecções falsas (cobrir com superfície lisa ou afastar). A fita escura na emenda da lona aparece em muitos quadros; não é objeto.

- **Medida temporária: celular como câmera IP** (2026-11-16), até a câmera nova: app "Android IP Camera" por HTTPS na rede local, `camera_index` com a URL do stream (`/video/mjpeg`), 1280×720, zoom 1,2, exposição e foco automáticos; 11–12 fps no Monitor e a cor muito melhor que a da DV20. O FFmpeg precisou mandar a senha já no primeiro pedido (`auth_type=basic` no `camera.py`): o app bloqueia com 429 os pedidos sem senha. Configuração e limitações em [`README.md`](README.md#celular-como-câmera-ip-medida-temporária-2026-11-16). Quadros capturados assim registram a URL no `captura.jsonl`; se entram na base fica para decidir com a câmera definitiva (condição diferente: outro sensor, exposição automática, Wi-Fi).

### Critérios para a câmera nova

Medidos na DV20 o que falta; a nova deve ter, conferido com o `ajustar_camera.py` antes de adotar:

| Critério | Por quê | Como conferir |
|---|---|---|
| UVC (sem driver) | Roda no Linux pelo V4L2, como o `camera.py` espera | `v4l2-ctl --list-devices` a mostra; `--list-formats-ext` lista formatos |
| 30 fps reais em 1280×720, em MJPG | A DV20 dá 12 em qualquer resolução; mais quadros por travessia, disparo mais preciso | `ajustar_camera.py --listar`, com a exposição manual curta já posta |
| Exposição manual que funciona, curta | Sem borrão com a esteira andando (alvo: ≤10 ms com a luz nova) | `--varrer exposicao`: o brilho muda com o valor, e o fps não cai |
| Ganho manual que funciona | Compensa a exposição curta | `--varrer ganho`: o brilho muda (na DV20, não muda) |
| Balanço de branco manual que funciona | Cor igual entre sessões | `--varrer temperatura_cor`: a cor muda (na DV20, não muda) |
| Foco manual (ou fixo nítido à altura da montagem) | Autofoco "caçando" borra quadros | `--varrer foco`, ou um quadro nítido da lona |
| Boa faixa dinâmica | Objeto claro sobre a lona preta sem estourar | Amostra com um objeto branco e um colorido: menos de 1% do quadro a 250+ e a lona com textura |
| Campo de visão que cubra a largura da esteira à altura possível | Sem cortar objetos nas bordas | Amostra: as duas bordas da lona no quadro |
| Valores lidos de volta iguais aos pedidos | O backend confere e registra; a DV20 informa valores internos errados | `ajustar_camera.py` sem argumentos sai com código 0 |

Obturador global não é preciso na velocidade desta esteira, se a exposição for curta. Com a câmera nova, refazer a 6b inteira (o bloco `camera` é de cada câmera).

**Logitech C920, conferida em 2026-11-18** (`/dev/video3`, apontada para a esteira, as duas bordas da lona no quadro): UVC ✅; MJPG 1280×720 a 29–30 fps com luz ✅ (YUYV: 10 fps em 720p); exposição manual ✅, mas só em valores discretos (78, 156, 312, 625, 1250…, em 100 µs; pedidos fora da lista ficam no anterior, e o `ajustar_camera.py` agora avisa); ganho manual ✅ (0–255, muda a imagem); balanço de branco e foco manuais existem (2800–7500 K, 0–250), efeito não medido; 0,5% do quadro a 250+ no automático com luz ✅. No automático e com pouca luz, chega a 125 ms de exposição e o fps cai para 15. A varredura de exposição não fechou: a luz da sala caiu no meio dela (brilho médio de 88 para 3). Adotado no `config.json` da máquina: `camera_index` 3, MJPG 1280×720 a 30, controles de imagem 128, `gama` `null`, o resto automático.

### Melhoria futura: luz controlada e exposição fixa

Decidido em 2026-11-18: por ora não há como garantir a iluminação da esteira, então o código não depende dela (exposição, ganho e balanço de branco automáticos; a captura com o motor desligado ignora mudanças globais de brilho). Custo aceito: a imagem muda com o que passa na esteira (um objeto escuro clareia o fundo, a lona escura pode estourar objetos claros), e com pouca luz o fps cai para 15. Quando a luz for controlada (luminária fixa dos dois lados da esteira, luz do dia bloqueada):

1. Refazer a 6b na C920: exposição entre 78, 156 e 312 (≤10 ms é a meta), ganho, temperatura de cor e foco; conferir cintilação da lâmpada (rede de 60 Hz) gravando ~30 quadros seguidos.
2. No início de cada sessão, comparar o brilho da lona vazia com o da calibração e avisar no log acima de ~15% de diferença (não implementado).
3. A partir daí, as sessões saem na mesma condição; as gravadas no automático ficam identificáveis pelo `captura.jsonl` (`exposicao` `null`).

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

**Máquina da esteira (decidido em 2026-11-16)**: a 6a é desenvolvida e testada na própria máquina que roda a esteira, em Linux (Fedora 43), com o backend V4L2 do OpenCV. A tradução para DSHOW (Windows, onde a equipe desenvolveu) entra só se for simples, e fica marcada como não testada no código e no `backend/README.md`.

### 6b. Calibração (primeiro passo na esteira)

Com a esteira montada, a iluminação que será usada sempre e objetos dos quatro materiais no campo:

1. **Iluminação** (adiada em 2026-11-18: ver [melhoria futura](#melhoria-futura-luz-controlada-e-exposição-fixa)): preferir luz artificial e fechar cortinas. Com exposição manual, a luz do dia variando muda o brilho entre sessões. Se não der para controlar, anotar a condição de cada sessão.
2. **Resolução e formato**: a maior com MJPG que mantém o fps do Monitor perto do de hoje (o YOLO é o gargalo; decodificar 1080p custa CPU). Provável 1280×720.
3. **Foco**: varrer `foco` e escolher o quadro mais nítido sobre a lona (a DV20 não tem foco ajustável: pular).
4. **Exposição**: varrer (na DV20, a unidade é de ~2 µs; na luz da sala, só ~60000 iguala o automático) e escolher a mais curta (menos borrão com a esteira andando) que não escurece os objetos escuros. Se escurecer, subir o `ganho` antes de alongar a exposição. Conferir com objetos brilhantes (lata, vidro): sem estourar.
5. **Balanço de branco**: a DV20 não tem o automático (fica sempre na `temperatura_cor` do driver, padrão 4500); varrer `temperatura_cor` e escolher o que deixa a lona e um papel branco neutros.
6. Gravar os valores no `config.json` e rodar `ajustar_camera.py` uma última vez: os valores lidos de volta iguais aos pedidos.
7. Rodar o backend sem captura e conferir as detecções do `best.pt` no Monitor. Se piorarem muito em relação ao automático, rever a exposição.

Os valores escolhidos valem para a operação e para a captura de todas as sessões; mudá-los depois cria uma condição nova, registrada no `captura.jsonl` de cada sessão. O `config.example.json` e os padrões não mudam: são de cada câmera.

## Etapa 7: sessão na esteira

Roteiro de 2026-11-16. Começa depois da 6b, com a câmera já fixada.

**Antes de ir**:
- ~~Recomendado: corrigir os itens 36 e 39 do `REFATORACAO.md`.~~ Feitos em 2026-11-16 (`9e83f65`): "Testar Conexão Serial" devolve o motor ao estado em que estava (antes, sempre terminava em `MOTOR OFF`: um clique na sessão parava a esteira sem aviso, com a captura passando ao ramo de motor desligado), e a serial é reaberta a cada 5 s depois de um cabo USB mexido (antes, modo demo até reiniciar). Testado com o ESP32 simulado num pty; falta conferir com o ESP32 de verdade.
- Na máquina da esteira: venv com `backend/requirements.txt`, `python -m pytest backend/tests` passando, `python backend/test_connection.py` achando a câmera e a porta, e `serial_port`/`camera_index` certos no `config.json` (a DV20 é o índice 2, não o 3).
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
