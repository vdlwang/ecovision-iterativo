# Problemas conhecidos — CyberReciclagem

Análise feita em 2026-10-08 por leitura do código, dos labels e da planilha `scripts/avaliacao_modelos_resultados_2.xlsx`. Nada foi executado: não havia `ultralytics` instalado nem ESP32 conectado.

**Níveis de complexidade:**

- 🟢 **Pontual:** correção local, de minutos.
- 🟡 **Moderado:** afeta um fluxo inteiro ou exige decidir algo.
- 🔴 **Estrutural:** envolve arquitetura, dados ou organização do projeto.

Os itens com ❓ são dúvidas em aberto (consolidadas no fim).

---

## 🔴 Estrutural

### E1. Dois sistemas de controle incompatíveis, e o firmware de um deles não está no repo

- `scripts/model.py`, `model_2.py`, `final_model.py` e `testes_serial.py` falam um protocolo de servo e motor: `50` (ângulo puro), `SERVO <n>`, `MOTOR ON`, `MOTOR OFF`, `PING`. O firmware que entende esses comandos **não está versionado**.
- O middleware (`interface/reciclagem_middleware_v1/`) envia `PULSE:<gate>,<ms>`, e `esp32_cancela.ino` aceita apenas `PULSE`, `OPEN` e `CLOSE`.
- Esse firmware liga e desliga pinos digitais (16/17/18), o que serve para relé ou solenoide, não para servo (servo precisa de PWM).
- Na prática, rodar `model_2.py` com o `.ino` do repo resulta em `ERR comando` para tudo.
- ❓ Qual é o hardware real: servo único com ângulos ou 3 cancelas on/off? Qual dos dois caminhos é o oficial? O histórico de commits ("functional version", "using webcam") sugere que é `model_2.py`.

### E2. O mapeamento de classes por substring não cobre os materiais do projeto

Afeta `model.py`, `model_2.py` e `final_model.py`. As chaves são `plastic`, `metal`, `cardboard` e `glass`, comparadas com os nomes das classes TACO:

- `"cardboard"` não existe em nenhuma das 61 classes TACO (lá o nome é *carton*). **Papelão nunca é separado.**
- `"metal"` não casa com `Drink can` nem com `Food Can`. **Latinhas nunca são separadas**, embora sejam uma das 6 classes do dataset. Por outro lado, casa com `Metal bottle cap`, `Metal lid` e `Scrap metal`.
- `Normal paper` não casa com nenhuma chave.
- `"plastic"` casa com 15 ou mais classes, `Plastic film` e `Garbage bag` entre elas.

**Correção sugerida:** mapear por ID de classe, como o middleware já faz em `ALVOS` (IDs 5, 6, 7, 12, 17, 33).

### E3. O modelo não foi treinado com dados do projeto

- Os `.pt` em `yolo_models/taco/` foram treinados só no TACO.
- Os 4 datasets próprios têm apenas o split `validation`, com cerca de 24 imagens e 100 anotações cada.
- Na planilha, o mAP@0.5 fica entre 0,34 e 0,64, com recall abaixo de 0,25 em várias classes. O yolov8m é pior que o yolov8s, o que indica *domain gap* e amostra pequena, não falta de capacidade do modelo.
- ❓ O fine-tuning com fotos da esteira está planejado? Se estiver, faltam os splits `train/` e `test/`, que os `data.yaml` já referenciam mas não existem.

### E4. Repositório pesado: 1,3 GB de dados e 739 MB de `.git`

- As fotos têm cerca de 9,5 MB cada (resolução de celular) e cada uma está gravada **3 vezes**: em `COCO_dataset/`, em `YOLO_dataset/validation/images/` e uma versão menor em `.thumbnail/`.
- Os pesos `.pt` (83 MB) estão no git sem LFS.
- `database/tcc-0SF/YOLO_dataset/validation/labels.cache` está commitado.
- **Sugestão:** usar Git LFS ou armazenamento externo e redimensionar as imagens para cerca de 1280 px. Isso não altera o resultado com `imgsz=640`.

### E5. Sem configuração centralizada nem código compartilhado

- `PORT = "COM5"`, caminhos de modelo, ângulos e `CONF` estão repetidos em 6 arquivos.
- As funções `send_line` e `read_reply` foram copiadas 3 vezes.
- O mapeamento das 6 classes aparece em 3 lugares: `val.py`, `example_integration_ultralytics.py` e `middleware_gui.py`.
- Não há `requirements.txt`, embora o README do middleware cite um.

---

## 🟡 Moderado

### M1. `scripts/val.py:59`: métricas por classe com rótulos trocados ⚠️ afeta os resultados do TCC

- `metrics.box.p[idx]` segue a ordem de `ap_class_index`, que são as classes presentes em ordem crescente: 5, 6, 7, 12, 17, 33.
- O código, porém, percorre `id_interesse = [6, 33, 17, 12, 7, 5]`.
- Se o comportamento do Ultralytics se confirmar, as colunas da planilha mostram a classe errada:

| Coluna na planilha | Classe real |
|---|---|
| glass bottle | plastic bottle |
| normal paper | glass bottle |
| corrugated carton | plastic bottle cap |
| metal drink can | metal drink can ✅ (coincidência) |
| plastic bottle cap | corrugated carton |
| plastic bottle | normal paper |

- ❓ Confiança alta, mas sem execução. Para confirmar, rode `print(metrics.box.ap_class_index)`.
- **Correção:** `i = list(metrics.box.ap_class_index).index(class_id)` e então `metrics.box.class_result(i)`.

### M2. `scripts/model_2.py:144`: um mesmo objeto aciona o servo várias vezes

- O debounce (`DETECTION_COOLDOWN`) é global e baseado só em tempo.
- Quando um objeto é detectado na ROI a esteira **para**, e o objeto continua parado dentro da ROI.
- Durante os ~5,5 s de atuação ele é enfileirado de novo a cada 1 s, o que gera 4 ou 5 acionamentos fantasmas.
- **Correção:** usar tracking (`model.track` com IDs) ou ignorar detecções enquanto `processing=True`.

### M3. `scripts/model_2.py`: a geometria entre câmera e desviador não é considerada

- O servo atua no instante em que o objeto cruza a ROI, e a esteira para nesse mesmo momento.
- ❓ O desviador fica logo abaixo da câmera? Se estiver mais adiante, falta um atraso de transporte (distância ÷ velocidade).

### M4. `scripts/model.py:61`: o filtro de ângulo repetido descarta objetos

- `if angle != last_angle_sent` faz com que dois plásticos seguidos acionem só o primeiro.
- Também não há ROI: dispara assim que o objeto aparece em qualquer parte do frame.

### M5. Middleware: o acionamento não depende da posição do objeto

- Enquanto o objeto estiver visível, a GUI envia um `PULSE` a cada 300 ms de cooldown.
- No firmware, `delay(ms)` (`esp32_cancela.ino:28`) bloqueia o loop. Os pulsos se acumulam no buffer serial e continuam sendo executados depois que o objeto já passou.

### M6. `database/*/YOLO_dataset/data.yaml`: `path:` absoluto do Windows

- O caminho `C:/Users/vitor/Documents/...` faz `val.py` e `test-yolo-format.py` falharem em qualquer outra máquina.
- **Correção:** remover o `path:` ou torná-lo relativo.

### M7. `scripts/convert-to-yolo-format.py` está quebrado

- O caminho `../datasets/45-SF/45-SF.json` não existe.
- `labels_dir` espera um diretório, não um arquivo.
- O padrão `cls91to80=True` remapearia os IDs das classes.
- Os labels atuais estão corretos (IDs TACO e polígonos), então a conversão foi feita de outro jeito.
- ❓ Como os labels YOLO foram gerados? Vale documentar isso para conseguir reproduzir.

---

## 🟢 Pontual

| # | Local | Problema |
|---|---|---|
| P1 | `scripts/final_model.py:13-17` | `MODEL_SOURCE` é definido duas vezes. `USE_WEBCAM` não é usado. A inferência roda em `IMG`, um caminho `C:\Users\natha\...`, e não na webcam. |
| P2 | `scripts/final_model.py:44-50` | O ramo `glass` não envia nada mas chama `readline()` mesmo assim. `sleep(5)` bloqueia o stream a cada detecção. A serial é aberta no nível do módulo com `sleep(10)`. |
| P3 | `scripts/model.py:52` | `save=True` na webcam grava vídeo continuamente em `runs/`. |
| P4 | `middleware_gui.py:239,252` | Se o usuário digitar algo não numérico num Spinbox, `.get()` lança `TclError`. A exceção sai de `_poll_queue` antes do `root.after` (linha 227), e **a GUI para de processar detecções sem avisar**. |
| P5 | `middleware_gui.py:176` | Não espera o reset do ESP32 ao conectar, então os primeiros comandos podem se perder. Também nunca lê as respostas `OK ...`. |
| P6 | `esp32_cancela.ino:82` | `inbuf` cresce sem limite se nunca chegar `\n`. |
| P7 | `yolo_models/yolo11.py:3` | O caminho `./yolo/yolo11n.pt` não existe. O arquivo está em `yolo_models/yolo11n.pt`. |
| P8 | `scripts/test-yolo-format.py` | Imprime "base 1" fixo. Na prática duplica o `val.py`. |
| P9 | `interface/canva/interface.html:793` | Tem um script injetado do Cloudflare (`/cdn-cgi/challenge-platform`), sobra da exportação, que deve ser removido. |
| P10 | `scripts/model_2.py` | Os atalhos de teclado só funcionam no Windows (`msvcrt`). |
| P11 | `.gitignore` | Falta `*.cache`, `__pycache__/` e `.venv/`. |

---

## Dúvidas em aberto

1. **Hardware:** é um servo com ângulos (scripts) ou 3 cancelas on/off (middleware)? Onde está o firmware que aceita `MOTOR ON` e `SERVO`?
2. **Caminho oficial:** vale `model_2.py` ou o middleware com GUI? A `interface.html` deve ser ligada a algum deles?
3. **Geometria:** qual é a distância entre a câmera e o desviador, e qual a velocidade da esteira? (necessário para M3)
4. **Fine-tuning:** está planejado, ou o TCC avalia apenas o modelo TACO pré-treinado?
5. **CF/SF:** significa "com fundo" / "sem fundo"?
6. **M1:** confirmar com `print(metrics.box.ap_class_index)`. Se o resultado for `[5 6 7 12 17 33]`, as colunas da planilha atual estão trocadas.

## Prioridade sugerida

1. **M1:** pode invalidar os resultados do TCC.
2. **E2:** papelão e latas nunca são separados.
3. **M2:** gera acionamentos duplicados no protótipo.
4. **E1:** decidir depois de responder à dúvida 1.
