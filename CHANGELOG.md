# Mudanças desde a tese

O que mudou em relação à versão final do TCC, marcada pela tag `tese-final` (`vitor-scosta/Ecovision@d6f5181`). Para ver o código da tese: `git show tese-final:<caminho>`; para ver o que mudou num arquivo: `git diff tese-final -- <caminho>`. Cada item cita o commit.

**Estado:** as mudanças da refatoração (seções 2 a 5) estão na branch `feature/refactoring-original-code` e foram testadas sem hardware (ESP32 simulado num pty, fotos de `legado/` como câmera). A verificação com ESP32, câmera e interface é feita antes do merge, pelos blocos A a F do `REFATORACAO.md`. O firmware novo precisa ser regravado no ESP32 (`cd firmware && pio run -t upload`).

## 1. Repositório (2026-10-10 a 2026-10-20)

- A versão preliminar (`vitor-scosta/tcc-testes`) foi para `legado/` e a final (`vitor-scosta/Ecovision`) virou a raiz, com os dois históricos preservados (`727bdaf`, `e9f470b`). O código da final foi organizado em `frontend/`, `backend/` e `firmware/` (`ef7afa4`).
- `ecovision_local_modf.py` passou a ser o backend oficial, e o README foi dividido em um por pasta (`b7f8cc3`). `PROBLEMAS.md` foi para a raiz (`7007a0e`) e hoje guarda só problemas fora do código (`39b7b70`).
- `backend/config.json` deixou de ser versionado: é local de cada máquina e é criado com os padrões na primeira execução (`79ebc1e`). `.gitignore` cobre `.venv/` e `*.cache` (`3f4f909`).

## 2. Correções de comportamento

### Backend

- **Configuração pela UI:** o backend responde `get_config`, então os painéis mostram os valores reais em vez de padrões fixos, e "Salvar" não grava mais `model_path` vazio (que fazia o próximo start falhar) nem a chave `type` (`de008c6`).
- **Esteira não religa sozinha:** ao fim de um acionamento, o motor fica como o usuário deixou (`1ca641f`).
- **Câmera que falha** (URL errada, Wi-Fi) é reaberta a cada 5 s, em vez de a thread do YOLO morrer com o servidor no ar e sem vídeo (`f80bb71`).
- **Mapa TACO → material** cobre todas as classes do `best.pt` (`carded blister pack` fica `other`) e perdeu a chave morta `plastic glooves` (`3875788`).
- **FPS** medido em janelas de 1 s, em vez da média desde o início (`bc24683`).
- **Serial:** escrita com trava, e ninguém espera resposta; uma thread registra tudo o que o ESP32 envia. Antes, a thread do YOLO e o WebSocket escreviam sem trava, e a leitura bloqueava o loop por até 1,5 s e podia ler a resposta de outro comando (`2701579`).
- **Envio dos quadros:** um cliente lento perde quadros em vez de acumular envios e atrasar os outros; sem cliente conectado, o quadro nem é codificado (`c519981`).
- **Confiança vale na hora:** o modelo roda com piso 0,1 e o filtro por `confidence` é feito a cada quadro; antes, o slider só valia depois de reiniciar (`ed0e5c2`).
- **Estado do motor:** começa desligado e só muda quando o comando sai pela serial; antes, começava ligado e mudava até em modo demonstração, e o Monitor mostrava a esteira ligada sem ESP32. Quando o ESP32 reinicia (ex.: queda de tensão com o servo), o backend lê `ESP32 pronto.` e marca o motor desligado, como ele de fato fica (`403c5e1`).
- **`config.json` de versão anterior** sem alguma chave (ex.: `class_to_angle`) usa o padrão dela, com um aviso no log; antes dava `KeyError` no laço da câmera a cada 5 s (`5fe875b`).
- **Serial reconecta:** a porta é reaberta a cada 5 s, na partida e depois de uma queda (cabo USB mexido); antes, o backend ficava em modo demonstração até reiniciar. Uma reconexão não religa a esteira (`9e83f65`).
- `testes_serial.py` lê a porta do `config.json` (`05666aa`).

### Frontend

- **Cancelas:** o vidro usa a chave `glass` (com `vidro`, ele nunca acionava depois de salvar), os ângulos padrão são os do backend (50/150/130/110) e o texto não manda mais reiniciar o backend (`1b7cfbd`).
- **Câmera por URL:** o campo aceita URL de stream além do índice (`9601534`).
- **Seletor de modelo** lista os pesos TACO reais, com `best.pt` como padrão; antes oferecia `yolov8l`/`yolov8x`, que não existem, e não oferecia o `best.pt` (`cbdf60a`). O `yolov8s.pt` ficou fora da lista por ser tido como COCO; é TACO (veja `yolo_models/README.md`).
- **Status do Monitor:** mostra a porta serial real (ou "Demo"), e câmera/YOLO só aparecem ativos quando chegam quadros (`2cbf56f`).
- **Backend offline:** "Salvar" desabilitado (`026269d`); as páginas de configuração ficam bloqueadas, e os botões da esteira exigem serial (`5b24934`).
- **"Testar Conexão Serial"** devolve o motor ao estado em que estava (antes, sempre terminava em `MOTOR OFF`, parando a esteira que estava andando) e exige a serial ativa (`9e83f65`).
- **Badge de conexão ao trocar de painel:** um painel aberto com o socket já conectado mostrava "Backend Offline" (e bloqueava "Salvar") até o backend reconectar; o estado agora vem do socket compartilhado ao montar, e os listeners do socket não ficam mais órfãos ao sair do painel (`4052b4e`).
- **Canvas do Monitor** só é redimensionado quando o tamanho do quadro muda; antes, `width`/`height` eram reatribuídos a cada quadro, recriando o buffer do canvas umas 15 vezes por segundo. Suspeito (não confirmado) de dois travamentos do computador por falta de memória em 2026-11-24, com 8,2 GB de shmem sem dono no relatório do OOM, possivelmente buffers do i915 do Firefox (`f84d8d7`).

### Firmware

- Comando inválido responde `ERR: ...` e não move o servo (antes, `PING` virava 0°); ângulos fora de 0..180 são recusados; `PING` → `PONG`; o servo vai para 175° no boot; o LED da placa acende com o motor e pisca durante cada acionamento (`1f08106`).

## 3. Limpeza (sem mudança de comportamento)

- Backend: prints de debug por quadro e atalhos de teclado inexistentes removidos (`4a6ebd0`); variante antiga `ecovision_local.py` apagada (`5198a85`, está em `git show tese-final:backend/ecovision_local.py`).
- Firmware: versão antiga comentada e rampas de PWM mortas removidas (`55fd7da`).
- Frontend: 40 componentes, 34 dependências e imports sem uso do export do Figma removidos (`667766a`); dependências `"*"` fixadas, com `package-lock.json` (`51435e4`); `vite` só em `devDependencies` (`b5246b4`).

## 4. Padronização

- **Lógica de detecção** separada em `backend/deteccao.py`, sem câmera, serial nem YOLO (`53d7b51`).
- **Frontend:** URL do backend em `src/config.ts`, badge de conexão único (`BadgeBackend`) e ícone das detecções pelo material enviado pelo backend (`dd09a68`).
- **Caixas** desenhadas só pelo frontend, com label de classe, material e confiança do tamanho do texto; antes, cv2 e canvas desenhavam as duas (`822aceb`).
- **Logs** com `logging` (hora, nível, thread); `--debug=true` mostra cada comando ao ESP32 e as detecções de cada quadro, também via `run.sh`/`run.bat` (`fa797e9`, `6892bb2`; antes era a variável `ECOVISION_LOG=DEBUG`).
- **Versões fixadas** (`==`) em `backend/requirements*.txt`, testadas com Python 3.14; o mínimo passa a ser Python 3.12 (`3acfb23`).

## 5. Testes

- 25 testes pytest para `deteccao.py`, inclusive se toda classe do `best.pt` tem material (`7e54bfc`), e `test_requirements.py`, que confere as versões fixadas (`3acfb23`). Testes do estado do motor (`motor.py`, `403c5e1`), da captura (`captura.py`, `5fe875b`) e da câmera (`camera.py`, com uma câmera falsa, `6316da1`). Rodar com `python -m pytest backend/tests`.

## 6. Recursos novos

- **Rastreamento no acionamento** (T15): o YOLO roda com o ByteTrack (`model.track`), e o servo dispara uma vez por objeto, quando a trilha cruza a faixa (também se a pular entre dois quadros), com o material votado ao longo da trilha. Substitui o intervalo fixo de 1,5 s (`DETECTION_COOLDOWN`), que ignorava um segundo objeto próximo e podia disparar duas vezes pelo mesmo. Objeto que cruza com o servo ocupado gera um aviso no log. Detecções levam o `id` da trilha (WebSocket, `captura.jsonl`, etiqueta do Monitor). `lap` passa a ser dependência fixada.
- **Captura para a anotação** (T4 do `OBJETIVO.md`): com `--capturar=true` ou `captura.ativa`, o backend grava quadros da esteira espaçados no tempo (no mínimo a cada `intervalo_s`; com o motor desligado, só quando a cena muda), em JPEG com o horário UTC no EXIF, mais um `captura.jsonl` por sessão. Desligada por padrão; não muda a detecção nem o acionamento. Pillow passa a ser dependência fixada (`5fe875b`; detalhes no `backend/README.md`).
- **Câmera configurada** (T4, etapa 6a, `6316da1`): o backend abre a câmera ele mesmo (`camera.py`, V4L2 no Linux) e aplica o bloco `camera` do `config.json` (formato, resolução, fps, exposição, ganho, temperatura de cor, foco, `imgsz`), confere o que a câmera aceitou e registra tudo no log e no `captura.jsonl`. `null` em exposição, cor e foco religa o automático a cada abertura. Uma thread lê a câmera e guarda só o quadro mais recente, como fazia o Ultralytics; um vídeo como câmera é lido no seu ritmo. Sem o bloco, a câmera abre como antes. `ajustar_camera.py` lista formatos com o fps medido e varre exposição, cor, foco, ganho e os controles de imagem (brilho, contraste, saturação, nitidez, gama, também no bloco, para corrigir a imagem azulada com que a câmera da esteira liga). No Windows (DSHOW), sem teste (detalhes no `backend/README.md`).
- **Backend caía com stream de rede parado** (SIGSEGV dentro do FFmpeg): ao reabrir a câmera depois de 10 s sem quadro, a captura era solta com a thread de leitura ainda presa no `read()` do stream HTTPS. Agora só a própria thread a solta, quando o `read()` volta; com a webcam USB, o `read()` voltava logo e isso não aparecia.
- **Câmera IP com senha** (medida temporária, celular Android como câmera): para URL com usuário e senha, o OpenCV manda a senha já no primeiro pedido (`auth_type=basic` do FFmpeg); sem isso, o app de câmera IP passava a responder 429 e o stream não abria (detalhes no `backend/README.md`).
- **Captura por objeto novo** (T4): com o motor ligado, a captura automática deixa de ser um temporizador (uma foto a cada Δ, que saía com a lona vazia ou o objeto cortado na borda) e sai ~1 s (`atraso_s`) depois de um objeto entrar na lona, com Δ desde a última. O objeto é detectado pela diferença para a lona vazia, não pelo YOLO. Novos campos do bloco `captura`: `atraso_s`, `ocupacao_minima`, `limiar_bloco`. A miniatura subamostra o quadro antes (26 → ~2 ms em 1280×720), porque passa a rodar em todo quadro, e as linhas que não são quadro saem pela fila de gravação, na ordem certa no `captura.jsonl`.
- **Captura pelo Monitor** (T4): um card liga e desliga a captura automática com o backend rodando, e o botão "Capturar agora" grava o quadro atual na hora (fora das regras de intervalo e travessia, mas contando para o espaçamento da automática). O `captura.jsonl` registra a `origem` de cada quadro (`automatica` ou `manual`) e cada mudança da automática. `--capturar`/`captura.ativa` passam a dizer só se a automática começa ligada.
- **Câmera sem controle de luz** (T4, 6b revista): a câmera da esteira passa a ser a Logitech C920, com exposição, ganho e balanço de branco automáticos, porque a iluminação não é garantida (fixá-los fica como melhoria futura). A captura com o motor desligado compara os quadros com o brilho médio igualado, para a exposição automática não disparar capturas sem a cena mudar; o `ajustar_camera.py --varrer` avisa quando o driver ignora o valor pedido (a C920 só aceita alguns valores de exposição).
- **Foco pelo Monitor**: um card trava o foco da câmera onde o autofoco o deixou, religa o autofoco ou o põe à mão por um slider, com o backend rodando. A thread da câmera aplica o pedido entre duas leituras, e o valor vai ao `camera.foco` do `config.json`. O quadro enviado ao frontend traz o `foco` lido da câmera. Testado com a C920.
- **Exposição pelo Monitor**: um card como o do foco trava a exposição no nível em que o automático estava, religa o automático ou a põe à mão por um slider (escala logarítmica, 3 a 2047 na C920). Travar fixa também o ganho: a C920, ao sair do automático, volta ao último ganho posto à mão, e a imagem escurecia (brilho médio 108 → 39 na medida). Exposição e ganho vão ao `camera.exposicao` e `camera.ganho` do `config.json` (`null` de volta no automático), e o quadro traz a `exposicao` lida (`auto`, `valor`, `ganho`). O foco e a exposição passam pelo mesmo `LeitorCamera.pedir` e pelo mesmo card no frontend (`AjusteCamera.tsx`). Travamento testado com a C920 pelo `v4l2-ctl`, com o brilho do quadro medido.
- **Ganho pelo Monitor**: um slider de ganho (0 a 255) no card da exposição, só com a exposição manual (na automática, o backend recusa e o slider fica desabilitado), gravado em `camera.ganho`; mensagem `{"type": "ganho", "valor"}`. Serve para clarear a exposição curta que evita o borrão: com a esteira a ~610 px/s, a exposição 156 borrava ~9 px, e a 39 deixou o texto do pacote legível. O slider do card virou o componente `SliderAjuste`, usado pelos dois.
- **Exposição só nos valores que a C920 aceita**: o slider da exposição parecia não funcionar. A C920 só aceita 5, 10, 20, 39, 78, 156, 312, 625, 1250 e 2047 (medido pelo `v4l2-ctl` e pelo brilho dos quadros); com outro valor, vai a 156, e a leitura logo depois ainda mostra o pedido, então o Monitor mostrava "Fixo em 200" com a câmera em 156. Travar tinha o mesmo problema (o automático para em valores como 209). O backend agora leva todo pedido ao valor aceito mais próximo (`camera.exposicoes_aceitas`, padrão a lista da C920), e o slider só para nesses valores, em vez da escala logarítmica de 3 a 2047.
- **Tempos da captura automática pela travessia medida**: um objeto leva ~3 s para cruzar o quadro (2026-11-24), então os padrões passam a `travessia_s` 3 (antes 5), `atraso_s` 1,5 (antes 1; ~metade da travessia, com o objeto perto do centro) e Δ `intervalo_s` 4 (antes 10; acima da travessia, com folga). Com Δ 10, um objeto que entrasse até 10 s depois da última captura se perdia; agora só até 4 s. O `--janela` padrão do `importar.py` (e do `pipeline.py`) acompanha, de 10 para 4 s: com 10, as capturas a 4–10 s uma da outra formariam uma cadeia, e a sessão inteira iria a um conjunto só.
- **Captura por objeto com a lona irregular andando** (T4): a referência única da lona vazia (uma foto, brilho igualado) dá lugar a um **teto por bloco**: o maior brilho que cada bloco da miniatura teve com a lona vazia andando por `aprendizado_s` (20 s, mais que uma volta), sem igualar o brilho; um bloco acima do teto mais `margem_teto` (20) está ocupado. Na esteira em 2026-11-24, a lona vazia andando (emenda, manchas, a mancha de luz, quadro escuro amplificado ~3× pela igualação) dava 10–55% de ocupação: a referência nunca era confirmada, era refeita a cada 9 s, e nenhum objeto disparava a captura com o motor ligado. Com o teto, nos quadros da sessão: lona vazia até 0,3%, a lata 10%. O teto é aprendido de novo ao ligar a automática e ao mudar foco, exposição ou ganho; pede a exposição travada e só vê objetos mais claros que a lona. `limiar_bloco` sai do bloco `captura` (`a2e0487`).
- **Objetos pequenos na captura** (T4): há objeto quando o maior grupo de blocos vizinhos acima do teto tem `blocos_minimos` (6), em vez de 3% do quadro (`ocupacao_minima`, ~69 blocos), que deixava passar tampas (~10–25 blocos). O ruído da lona vazia sai em blocos soltos: maior grupo de 3 nos quadros de 2026-11-24, contra 220 da lata. O `captura.jsonl` grava o maior grupo (`regiao`).
- **Janela Δ na importação** (T4, `40e76d5`): o `anotacao/importar.py` lê o horário de captura (EXIF, senão o nome das fotos de celular) e põe no mesmo conjunto (treino ou teste) as imagens a menos de `--janela` segundos uma da outra, contando as já importadas; avisa se um grupo já estava nos dois conjuntos. O banco da anotação passa ao esquema v7 (`imagens.capturada_em`); saídas v6 são recusadas e têm de ser reimportadas (detalhes no `anotacao/README.md`).

## Ainda como na tese

- O acionamento não acompanha a posição do objeto na esteira (5 s fixos por objeto). Fica para um módulo de rastreamento, fora da refatoração.
- `docs/diagrams/` ainda descreve a arquitetura proposta na tese; os diagramas serão refeitos com os módulos novos.
- O login continua simulado.
