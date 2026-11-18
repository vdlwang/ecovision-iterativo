# Backend - EcoVision

Processo Python que junta câmera, YOLO, WebSocket e serial. Visão geral do sistema no [README principal](../README.md).

## Execução

```bash
pip install -r requirements.txt
python ecovision_local_modf.py      # pode ser chamado de qualquer pasta
```

As versões em `requirements.txt` são fixas (`==`), as testadas com Python 3.14; o numpy 2.5 exige Python 3.12+. Para usar a GPU, instale antes a build CUDA do `torch` da mesma versão (instruções em pytorch.org); o pip a aceita no lugar da fixada. Para atualizar, troque todas as versões juntas, rode os testes e o bloco de verificação, e só então retreine o modelo.

- **`ecovision_local_modf.py`** é o backend oficial (é o que `run.sh` e `run.bat` sobem). O YOLO roda com rastreamento (abaixo, "Rastreamento"): cada objeto dispara o servo uma vez, quando cruza a ROI, e o sistema fica ocupado por `servo_actuation_seconds`.
- **`motor.py`** guarda o estado do motor (`EstadoMotor`), e **`captura.py`** a captura para a anotação (abaixo); ambos sem câmera nem serial, testáveis sem hardware.
- **`camera.py`** abre a câmera, aplica o bloco `camera` do `config.json` e a lê numa thread própria, entregando ao YOLO só o quadro mais recente (abaixo, "Câmera"). **`ajustar_camera.py`** é a ferramenta de calibração.
- **`deteccao.py`** guarda a lógica que não depende de câmera nem de serial: a tabela `taco_to_material`, o filtro das caixas pela confiança (`deteccoes_do_quadro`) e a decisão de disparar o servo (`angulo_a_disparar`).
- A variante anterior, `ecovision_local.py`, enfileirava os materiais detectados e os enviava um a um, usando `detection_cooldown`. Foi removida; está na tag `tese-final` (`git show tese-final:backend/ecovision_local.py`).

O WebSocket escuta em `ws://localhost:8765`. Se a porta serial não abrir, o backend segue em modo demonstração: detecta e transmite, mas não aciona o ESP32. A thread `serial` tenta abrir a porta a cada 5 s (`SERIAL_RETRY_SECONDS`), na partida e depois de uma queda (cabo USB mexido, falha de escrita ou leitura), e sai do modo demonstração sozinha quando consegue. O motor só é ligado na conexão da partida: uma reconexão não religa a esteira. Abrir a porta reinicia o ESP32, que volta com o motor parado; o backend lê `ESP32 pronto.` e marca o motor desligado. Se o sistema der outro nome à porta depois de reconectar o cabo (`/dev/ttyACM0` vira `/dev/ttyACM1`), a reconexão não a acha: corrija `serial_port` e reinicie.

### Logs

O backend registra com `logging` no terminal, no formato `hora nível [thread] mensagem` (threads `MainThread`, `yolo`, `camera`, `serial` e, com a captura, `captura`). Em INFO, o padrão, saem a inicialização, as conexões de clientes, cada disparo (`Disparando: classe → material → ângulo`), as linhas que o ESP32 envia e as mudanças de configuração. Falhas de serial e de câmera saem em WARNING/ERROR. Para ver também cada comando enviado ao ESP32 (`→ ESP32: ...`) e as detecções de cada quadro:

```bash
python ecovision_local_modf.py --debug=true
../run.sh --debug=true      # ou run.bat --debug=true: o argumento vai para o backend
```

`--debug` sozinho equivale a `--debug=true`; o padrão é `false`. Um valor que não seja verdadeiro/falso (`true`/`false`, `1`/`0`, `sim`/`não`) faz o backend sair com erro de uso.

As bibliotecas (websockets etc.) só aparecem a partir de WARNING.

## `config.json`

Lido na inicialização a partir de `backend/config.json`. Se o arquivo não existir, é criado com os valores padrão (`CONFIG_PADRAO`). Se faltar alguma chave (um `config.json` de versão anterior, sem `class_to_angle` ou sem `captura`), o backend usa o padrão dela e avisa no log; o arquivo só é regravado quando a UI salva. É configuração local da máquina e está no `.gitignore`. O frontend também grava neste arquivo ao clicar em "Salvar". O `config.example.json` traz os mesmos valores padrão, como referência para editar à mão (por exemplo, `cp config.example.json config.json`).

| Campo | Uso |
|-------|-----|
| `serial_port`, `baud_rate` | Porta do ESP32 (`COM8` / `/dev/ttyUSB0`) e velocidade (115200) |
| `camera_index` | Índice da webcam no OpenCV, ou URL de um stream (ex.: `http://<ip>:8080/video` do app IP Webcam; a página `.html` do app não serve) |
| `model_path` | Pesos do YOLO. Caminho relativo é resolvido a partir de `backend/`. Padrão: `../yolo_models/taco/best.pt` (veja [`yolo_models/README.md`](../yolo_models/README.md)) |
| `confidence` | Confiança mínima das detecções. O YOLO roda com `CONF_MINIMA_MODELO` (0.1) e o filtro é feito a cada quadro, então vale na hora (valores abaixo de 0.1 só depois de reiniciar) |
| `roi_y_min`, `roi_y_max` | Faixa horizontal do quadro (fração da altura) em que o centro do objeto dispara o servo |
| `class_to_angle` | Ângulo do servo por material: chaves `plastic`, `metal`, `glass`, `paper` |
| `servo_actuation_seconds` | Tempo em que o sistema fica ocupado após cada disparo |
| `captura` | Captura de quadros para a anotação (abaixo): `ativa`, `pasta`, `intervalo_s`, `travessia_s`, `diferenca_minima`, `qualidade_jpeg` |
| `camera` | O que pedir à câmera (abaixo, "Câmera"): `largura`, `altura`, `fourcc`, `fps`, `exposicao`, `temperatura_cor`, `foco`, `ganho`, `imgsz` |
| `detection_cooldown` | Ignorado (era usado pela variante removida `ecovision_local.py`); o disparo é uma vez por objeto rastreado |

`serial_port`, `baud_rate`, `camera_index`, `camera` e `model_path` só passam a valer depois de reiniciar o backend. `confidence`, `class_to_angle` e a ROI valem na hora.

## Captura para a anotação (T4)

Grava quadros da esteira para o ciclo de anotação (`anotacao/`, tarefa T4 do [`OBJETIVO.md`](../OBJETIVO.md); plano em [`PLANO-CAPTURA.md`](PLANO-CAPTURA.md)). Desligada por padrão; liga com `captura.ativa` no `config.json` ou na linha de comando, que tem prioridade:

```bash
python ecovision_local_modf.py --capturar=true     # --capturar sozinho equivale a true
../run.sh --capturar=true
```

Quando grava:

- nunca a menos de `intervalo_s` (Δ, padrão 10 s) da captura anterior;
- **motor ligado**: a cada Δ, depois de `travessia_s` (padrão 5 s) desde que o motor ligou. Com a esteira em velocidade constante, o tempo dá o deslocamento: com Δ acima do tempo de um objeto cruzar o campo da câmera, o mesmo objeto não aparece em duas capturas, e a espera depois de ligar evita gravar de novo o que estava parado no campo. Meça a travessia na esteira e ajuste os dois valores;
- **motor desligado ou modo demonstração**: só quando o quadro difere do último gravado (diferença média em cinza, numa miniatura, de pelo menos `diferenca_minima`, padrão 10 em 0–255): objetos postos à mão, esteira parada. As duas miniaturas são escaladas para o mesmo brilho médio antes de comparar: com a exposição no automático, a câmera clarear ou escurecer o quadro inteiro não conta como cena nova (num quadro da C920, 30% mais escuro dava 26 sem isso, e dá 0); um objeto posto ou tirado continua contando (~20 para a faca da amostra).

O estado do motor é o do último comando que saiu pela serial. A captura independe de haver cliente no WebSocket e não muda a detecção nem o acionamento.

Cada execução que grava cria `<pasta>/<AAAAMMDDTHHMMSS>/` (padrão `backend/capturas/`, no `.gitignore`; caminho relativo é resolvido a partir de `backend/`), com:

- um JPEG por quadro, na resolução em que a câmera entrega (a do bloco `camera`, abaixo; sem ele, a padrão do driver), qualidade `qualidade_jpeg` (95), sem as caixas, com nome `<AAAAMMDDTHHMMSS.mmm>Z.jpg` e o horário de captura em UTC no EXIF (`DateTimeOriginal`, `SubSecTimeOriginal`, `OffsetTimeOriginal`), que a importação usa para conferir que duas imagens não são próximas demais;
- `captura.jsonl`: a primeira linha (`"tipo": "sessao"`) com o bloco `captura`, a câmera (o relatório da abertura: pedido, lido de volta, divergências, resolução, formato e fps efetivos, `imgsz`), o modelo e a confiança; uma linha `"tipo": "camera"` a cada reabertura da câmera durante a sessão; e uma linha por quadro (`"tipo": "quadro"`), com arquivo, horário, largura, altura, `motor_ligado`, a diferença para o anterior (motor desligado) e as detecções do YOLO.

A gravação roda numa thread própria (`captura`), com fila de 4 quadros: o YOLO não espera o disco, e um quadro que não cabe na fila é descartado com um aviso. Ao encerrar com Ctrl+C, a fila é gravada antes de sair, e o log diz quantos quadros foram gravados.

## Câmera

O backend abre a câmera (`camera.py`) e aplica o bloco `camera` do `config.json`, para que os quadros da operação e os da captura saiam numa condição fixa e registrada. Antes, o Ultralytics abria a câmera só pelo índice, na resolução, no formato e na exposição padrão do driver; a exposição automática muda a imagem conforme o que passa na esteira.

| Campo | Padrão | Uso |
|---|---|---|
| `largura`, `altura` | `null` | Resolução pedida (ex.: 1280×720). Na DV20, use 1280×720: o sensor é 16:9, e 640×480 mostra o mesmo campo espremido na horizontal (objetos distorcidos), não um campo maior nem menor |
| `fourcc` | `null` | Formato do stream, ex.: `"MJPG"`. Em YUYV, resolução alta cai para ~10 fps; sem `fourcc`, a câmera da esteira (DV20) abre em YUYV 640×480 a 10 fps |
| `fps` | `null` | Taxa pedida |
| `exposicao` | `null` | `null` = automática; número = manual, na unidade do driver (V4L2: `exposure_time_absolute`; a DV20 aceita 80 a 100000, em ~2 µs e não nos 100 µs da especificação: 60000 ≈ 120 ms já derruba o fps para 8; escolha pela varredura) |
| `temperatura_cor` | `null` | `null` = balanço de branco automático; em kelvin = manual. A DV20 não tem o automático, e o manual é aceito e lido de volta mas não muda a imagem (3500 a 6500 dão o mesmo quadro) |
| `foco` | `null` | `null` = autofoco; número = foco manual fixo (a DV20 não tem foco) |
| `ganho` | `null` | Ganho manual; `null` = não mexer. Na DV20, aceito e lido de volta, mas sem efeito na imagem |
| `brilho`, `contraste`, `saturacao`, `nitidez`, `gama` | `null` | Controles de imagem, na unidade do driver; `null` = não mexer. Na DV20, use-os: ela liga com valores internos que dão uma imagem azulada, enquanto o driver informa 0 (e 0 posto de verdade deixa a imagem preta). Escolhidos em 2026-11-16: 0, 256, 384, 128, 20 |
| `imgsz` | `640` | Tamanho de entrada passado ao YOLO (o `best.pt` treinou com 640) |

- **Automáticos postos de forma explícita**: `null` em `exposicao`, `temperatura_cor` e `foco` religa o automático a cada abertura. No Linux, o driver guarda o último valor que qualquer programa pôs (o `ajustar_camera.py`, o `v4l2-ctl`) até a câmera ser desconectada. Uma câmera sem o controle automático só fica sem ele, sem aviso.
- **Conferência**: depois de aplicar, o backend lê cada valor de volta. Uma divergência (a câmera ignora ou arredonda: pedir 1366×768 e receber 1280×720) sai em WARNING e vai ao `captura.jsonl`, sem derrubar o backend. O log de INFO da abertura diz a resolução, o formato e o fps efetivos.
- **Leitura**: uma thread (`camera`) lê sem parar e guarda só o quadro mais recente, e o YOLO pega o último a cada volta. Sem quadro novo por 10 s (`ESPERA_QUADRO_S`), ou no fim de um vídeo, a câmera é reaberta depois de 5 s, com o bloco reaplicado.
- **Vídeo e URL**: um arquivo de vídeo como `camera_index` é lido no ritmo do seu fps, como uma câmera, e termina no fim; a uma URL de stream nada se aplica (o backend avisa se o bloco estiver preenchido).
- **Sistema**: testado no Linux (V4L2, Fedora 43, na máquina da esteira). No Windows, abre com DSHOW, e a tradução (`AUTO_EXPOSURE` 0,25/0,75, exposição em log2 de segundos) segue a documentação do OpenCV, **sem teste**.
- **Sem controle de luz (decidido em 2026-11-18)**: a iluminação da esteira não é garantida, então exposição, ganho e balanço de branco ficam no automático (`null`), e só formato, resolução, fps e os controles de imagem são fixados. Fixar a exposição fica como melhoria futura, junto com a luz (`PLANO-CAPTURA.md`, 6b).
- **C920 (Logitech, câmera da esteira desde 2026-11-18)**: `camera_index` 3 (`/dev/video3`; pode mudar com outras câmeras ligadas: confira com `v4l2-ctl --list-devices`), MJPG 1280×720 a 30 fps (29–30 medidos com luz), controles de imagem no padrão 128 e `gama` `null` (a C920 não tem gama; o contraste e a saturação da DV20, 256 e 384, passam do máximo dela, 255). Com pouca luz, a exposição automática chega a 125 ms e o fps cai para 15. A exposição manual só aceita alguns valores (78, 156, 312, 625, 1250…, em 100 µs); um valor fora da lista é ignorado em silêncio, e a conferência o acusa como divergência.
- **Índice no Linux**: cada câmera UVC cria dois nós, `/dev/videoN` (vídeo) e `/dev/videoN+1` (metadados, sem formatos). O `camera_index` é o do nó de vídeo: a DV20 hoje é o 2, não o 3. `v4l2-ctl --list-devices` mostra os nós.

### Celular como câmera IP (medida temporária, 2026-11-16)

Até a câmera nova chegar (critérios no [`PLANO-CAPTURA.md`](PLANO-CAPTURA.md), etapa 6b), a esteira é testada com um celular Android rodando o app "Android IP Camera" (página de título *Android IP Camera*, HTTPS com certificado próprio, porta 4444, login e senha). A DV20 continua configurada no bloco `camera`; para voltar a ela, `camera_index: 2`.

- **URL no `camera_index`**: a do stream, com as credenciais: `https://<usuário>:<senha>@<ip>:4444/video/mjpeg`. A raiz (`/`) é a página do app, não o vídeo. Caracteres especiais na senha vão codificados (`@` → `%40`).
- **Senha já no primeiro pedido**: o FFmpeg (que o OpenCV usa para URL) pede primeiro sem senha e só a manda depois do 401; este app passa a responder **429 Too Many Requests** a todo pedido sem senha depois de alguns desses, e o stream não abre mais. O `camera.py` liga `auth_type=basic` do FFmpeg (variável `OPENCV_FFMPEG_CAPTURE_OPTIONS`) para URL com usuário e senha, e o problema some. Com o `curl`, o mesmo: `curl -sk -u usuário:senha https://<ip>:4444/video/mjpeg`.
- **No navegador**, a página do app fica com o vídeo preto se aberta com `usuário:senha@` no endereço (o Chrome recusa o `fetch` do vídeo a partir de um endereço com credenciais). Abra `https://<ip>:4444/` sem elas, aceite o certificado e digite o login na janela. O app aceita poucos clientes no stream: com a página aberta, o backend pode não conseguir abrir.
- **Ajustes no app**, pela página ou por `curl -sk -u usuário:senha "https://<ip>:4444/?<controle>=<valor>"`: `resolution` (ex.: `1280x720`; o celular em pé entrega 720×1280), `zoom` (digital, corta pelo centro), `exposure` (compensação, −10 a 10), `focus_distance` (−1 = autofoco), `contrast`, `fps`. O estado fica em `https://<ip>:4444/info.json`. O bloco `camera` do `config.json` não se aplica a URL (o backend avisa no log).
- **Adotado em 2026-11-16**: lente traseira principal, `resolution=1280x720`, `zoom=1.2` (o máximo sem cortar a borda direita da lona, que está deslocada no quadro; para mais, centralizar o celular sobre a esteira), exposição e foco automáticos. Medido: 720×1280, ~9 fps lendo o stream sozinho, 11–12 fps no Monitor, 0,3% do quadro estourado com o pacote colorido sobre a lona (a DV20 estourava 7%). Com `resolution` padrão (960×720) o fps sobe para ~14.
- **Manter o app na frente e a tela ligada** (e o celular na tomada): com a tela apagada ou o app em segundo plano, o servidor do app para de responder (o celular ainda responde ao ping), o stream trava e o backend reabre a câmera a cada 5 s até o app voltar.
- **Limitações**: Wi-Fi (atraso e quadros perdidos pesam no acionamento do servo; conferir o fps no Monitor; o ping ao celular deu 170–220 ms com o Wi-Fi dele em economia de energia), bateria e aquecimento do celular, a sombra do suporte da DV20 na lona, e o celular em pé faz a esteira correr de cima para baixo no quadro (o sentido que a faixa `roi_y_min`/`roi_y_max` espera). A URL com a senha aparece no log e no `captura.jsonl` (pendente: mascarar).

### Calibração (`ajustar_camera.py`)

Com o backend parado (a câmera só abre num programa por vez):

```bash
python ajustar_camera.py                                 # aplica o bloco camera, mostra o lido de volta, mede o fps e grava amostra.jpg
python ajustar_camera.py --listar                        # formatos e resoluções (v4l2-ctl, se houver), com o fps medido
python ajustar_camera.py --varrer exposicao 500 2000 8000 20000   # um quadro por valor
python ajustar_camera.py --varrer temperatura_cor 3500 4500 5500
python ajustar_camera.py --camera 2 --listar             # outra câmera que a do config.json
```

`--varrer` aceita `exposicao`, `temperatura_cor`, `foco`, `ganho`, `brilho`, `contraste`, `saturacao`, `nitidez` e `gama`, parte do bloco `camera` do `config.json` e muda só o campo varrido. Os quadros vão para `capturas/ajuste/<AAAAMMDDTHHMMSS>/`, com o valor no nome, e cada linha impressa diz o valor lido de volta e o brilho médio, com `IGNORADO pelo driver` quando o lido difere do pedido (o quadro é então do valor lido). O roteiro da calibração está na etapa 6b do [`PLANO-CAPTURA.md`](PLANO-CAPTURA.md). Sem argumentos, o programa sai com código 1 se houver divergência.

## Rastreamento (T15)

O YOLO roda com `model.track(..., persist=True, tracker="bytetrack.yaml")` (ByteTrack do Ultralytics; dependência `lap`): cada caixa traz o ID da trilha do objeto (`id` nas detecções do WebSocket e do `captura.jsonl`; o Monitor o mostra como `#id`). A decisão é de `deteccao.DisparosPorTrilha`:

- **Uma vez por objeto:** a trilha dispara quando o centro dela está na faixa `roi_y_min`..`roi_y_max` ou a atravessou desde o quadro anterior (a 12 fps, um objeto rápido pode pular a faixa). Um objeto parado na faixa não dispara de novo, e dois objetos próximos disparam os dois, se o servo estiver livre. Substitui o intervalo fixo de 1,5 s entre disparos (`DETECTION_COOLDOWN`), que ignorava o segundo objeto e podia disparar duas vezes pelo mesmo.
- **Material votado:** a soma das confianças por material em todos os quadros da trilha (sem `other`), não a classe do quadro do disparo. O log diz os votos: `Disparando: #4 → plastic → 50° (votos: plastic 5.9)`.
- **Servo ocupado:** depois de um disparo, o sistema fica ocupado por `servo_actuation_seconds` (o firmware segura cada ângulo 5 s). Uma trilha que cruza a faixa ocupada ainda dispara se estiver dentro dela quando o servo liberar; se sair sem disparar, o log avisa: `Objeto #5 cruzou a faixa com o servo ocupado e não foi separado`. Antes, era ignorada sem registro.
- **Troca de ID:** se o rastreador perde um objeto já disparado e o acha de novo com outro ID (até 1 s depois, sobrepondo a última caixa), o novo ID herda o disparo.
- **Reabertura da câmera:** as trilhas recomeçam (`persist=False` no primeiro quadro).
- Só o que o rastreador confirmou vira detecção: uma caixa vista num quadro isolado não aparece no Monitor.

Conferido em 2026-11-16 com vídeos sintéticos (recortes das fotos da equipe descendo sobre um quadro real da esteira, a 12 fps): cada objeto detectado disparou uma vez, com o material certo; dois objetos a 0,75 s um do outro dispararam os dois com o servo livre em 0,5 s, e com 5 s o segundo gerou o aviso. Falta conferir na esteira.

## Detecção

Cada classe TACO detectada é convertida em material pela tabela `taco_to_material` de `deteccao.py` (por exemplo, `drink can` → `metal`, `corrugated carton` → `paper`). Classes fora dos quatro grupos viram `other` e não acionam o servo.

## Protocolo WebSocket (JSON)

Do frontend para o backend:

| Mensagem | Efeito |
|----------|--------|
| `{"command": "MOTOR ON"}` / `{"command": "MOTOR OFF"}` | Liga ou desliga a esteira |
| `{"command": "<ângulo>"}` | Move o servo direto (botão "Testar") |
| `{"type": "config", "confidence": <n>}` | Atualiza a confiança em memória |
| `{"type": "get_config"}` | Pede a configuração atual (os painéis enviam ao conectar) |
| `{"type": "save_config", ...}` | Mescla os campos no `config.json` e salva (a chave `type` não é gravada) |

Do backend para o frontend:

- Um por quadro: `{"frame": <jpeg base64, sem as caixas>, "detections": [{"class", "material", "confidence", "bbox", "id"}], "fps", "motor_running", "serial_port"}`. `serial_port` é `null` em modo demonstração. `motor_running` é o último comando de motor que de fato saiu pela serial: começa `false`, não muda em modo demonstração e volta a `false` quando o ESP32 reinicia (o backend lê `ESP32 pronto.`). Quem quiser as caixas desenha a partir de `detections` (o Monitor faz isso no canvas).
- Resposta a `get_config`, só para quem pediu: `{"type": "config", ...campos do config.json}`.

## Testes automatizados

```bash
pip install -r requirements-dev.txt
python -m pytest tests               # de backend/; da raiz: python -m pytest backend/tests
```

Cobrem `deteccao.py`, `motor.py`, `captura.py`, `camera.py` (com uma câmera falsa: ordem das propriedades, tradução por sistema, divergências, URL, leitor) e os requirements (`test_requirements.py`: toda dependência com `==`, e a versão instalada igual à fixada; pacote ausente é pulado). Em `deteccao.py`: o mapeamento TACO → material (inclusive se toda classe do `best.pt` tem entrada na tabela), o filtro por confiança e o disparo por trilha, com trilhas sintéticas (dois objetos próximos, objeto parado na faixa, faixa pulada entre dois quadros, classe oscilando, servo ocupado, troca de ID). Não precisam de câmera nem de ESP32. Câmera, serial, WebSocket e frontend continuam sendo testados à mão.

## Scripts de teste

```bash
python test_connection.py    # bibliotecas instaladas, câmera 0, portas seriais disponíveis e porta 8765 livre
python testes_serial.py      # REPL para mandar comandos ao ESP32 (porta e baud do config.json)
```

Os comandos aceitos estão em [`firmware/README.md`](../firmware/README.md). Com firmware anterior à continuação (tag `tese-final`), evite `PING`: ele é lido como 0 e move o servo para 0°.

## Troubleshooting

**"Could not open camera" / "Erro no stream da câmera":** o backend continua no ar e tenta reabrir a câmera a cada 5 s (`CAMERA_RETRY_SECONDS`). Tente outro `camera_index` (1, 2...). Com câmera de celular, use a URL do stream de vídeo (ex.: `http://<ip>:8080/video`), não a da página do app. No Linux, o usuário precisa estar no grupo `video` (`sudo usermod -a -G video $USER`).

**Porta serial não abre:**
- Confira a porta com `python test_connection.py`.
- Windows: instale o driver CH340/CP2102 do ESP32.
- Linux: adicione o usuário ao grupo `dialout` (`sudo usermod -a -G dialout $USER`) ou, temporariamente, `sudo chmod 666 /dev/ttyUSB0`.
- Feche o monitor serial do PlatformIO ou da Arduino IDE, que mantém a porta ocupada.
