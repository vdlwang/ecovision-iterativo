# Problemas conhecidos — CyberReciclagem

Análise feita em 2026-10-08 por leitura do código, dos labels e da planilha `legado/scripts/avaliacao_modelos_resultados_2.xlsx`. Nada foi executado: não havia `ultralytics` instalado nem ESP32 conectado.

Atualizado no mesmo dia após cruzar com o fonte da monografia (zip do Overleaf). Os problemas do texto estão na seção **Monografia**, no fim do arquivo.

> **Escopo:** a análise foi feita sobre a versão preliminar do TCC (`vitor-scosta/tcc-testes`), hoje em [`legado/`](legado/). Os itens E1–M7 e P1–P11 valem para esse código. Depois disso, a versão final (`vitor-scosta/Ecovision`) foi incorporada na raiz e tem o sistema descrito na monografia: frontend React + WebSocket, backend, firmware de servo/motor e o YOLOv8s com fine-tuning. Os itens que ela resolve estão marcados com ✅ **Resolvido pela versão final**. Os problemas conhecidos da versão final estão em [`README.md`](README.md#limitações-conhecidas).

**Níveis de complexidade:**

- 🟢 **Pontual:** correção local, de minutos.
- 🟡 **Moderado:** afeta um fluxo inteiro ou exige decidir algo.
- 🔴 **Estrutural:** envolve arquitetura, dados ou organização do projeto.

Os itens com ❓ são dúvidas em aberto (consolidadas no fim).

---

## 🔴 Estrutural

### E1. Dois sistemas de controle incompatíveis, e o firmware de um deles não está no repo

- `legado/scripts/model.py`, `model_2.py`, `final_model.py` e `testes_serial.py` falam um protocolo de servo e motor: `50` (ângulo puro), `SERVO <n>`, `MOTOR ON`, `MOTOR OFF`, `PING`. O firmware que entende esses comandos **não está versionado**.
- O middleware (`legado/interface/reciclagem_middleware_v1/`) envia `PULSE:<gate>,<ms>`, e `esp32_cancela.ino` aceita apenas `PULSE`, `OPEN` e `CLOSE`.
- Esse firmware liga e desliga pinos digitais (16/17/18), o que serve para relé ou solenoide, não para servo (servo precisa de PWM).
- Na prática, rodar `model_2.py` com o `.ino` do repo resulta em `ERR comando` para tudo.
- ✅ **Resolvido pela monografia:** o hardware real é 1 servo MG996R + ponte H L298N + 4 motores DC, o que corresponde ao protocolo dos `legado/scripts/`. Portanto o middleware e o `esp32_cancela.ino` estão **obsoletos** e poderiam ser removidos ou marcados como tal.
- ✅ **Resolvido pela versão final:** o firmware de servo/motor está em [`firmware/`](firmware/) e entende `MOTOR ON`, `MOTOR OFF`, `SERVO <n>` e `<n>`. `PING` não é reconhecido e move o servo para 0° (veja [`firmware/README.md`](firmware/README.md)).

### E2. O mapeamento de classes por substring não cobre os materiais do projeto

Afeta `model.py`, `model_2.py` e `final_model.py`. As chaves são `plastic`, `metal`, `cardboard` e `glass`, comparadas com os nomes das classes TACO:

- `"cardboard"` não existe em nenhuma das 61 classes TACO (lá o nome é *carton*). **Papelão nunca é separado.**
- `"metal"` não casa com `Drink can` nem com `Food Can`. **Latinhas nunca são separadas**, embora sejam uma das 6 classes do dataset. Por outro lado, casa com `Metal bottle cap`, `Metal lid` e `Scrap metal`.
- `Normal paper` não casa com nenhuma chave.
- `"plastic"` casa com 15 ou mais classes, `Plastic film` e `Garbage bag` entre elas.

**Correção sugerida:** mapear por ID de classe, como o middleware já faz em `ALVOS` (IDs 5, 6, 7, 12, 17, 33).

✅ **Resolvido pela versão final:** `backend/ecovision_local_modf.py` converte cada classe TACO em material por uma tabela explícita (`taco_to_material`), que cobre latas, papel e papelão. Os scripts de `legado/` continuam com o mapeamento por substring.

### E3. O modelo não foi treinado com dados do projeto

- Os `.pt` em `legado/yolo_models/taco/` foram treinados só no TACO.
- Os 4 datasets próprios têm apenas o split `validation`, com cerca de 24 imagens e 100 anotações cada.
- Na planilha, o mAP@0.5 fica entre 0,34 e 0,64, com recall abaixo de 0,25 em várias classes. O yolov8m é pior que o yolov8s, o que indica *domain gap* e amostra pequena, não falta de capacidade do modelo.
- ✅ **Resolvido pela monografia:** o fine-tuning do YOLOv8s foi feito (split 80/20, ~100 imagens), mas o script de treino e os splits não estão no repo. Veja também T2 na seção Monografia.
- ✅ **Resolvido pela versão final:** os pesos com fine-tuning estão em `yolo_models/taco/` (`best.pt` e anteriores; veja [`yolo_models/README.md`](yolo_models/README.md)).

### E4. Repositório pesado: 1,3 GB de dados e 857 MB de `.git`

- As fotos têm cerca de 9,5 MB cada (resolução de celular) e cada uma está gravada **3 vezes**: em `COCO_dataset/`, em `YOLO_dataset/validation/images/` e uma versão menor em `.thumbnail/`.
- Os pesos `.pt` (83 MB em `legado/`; 289 MB somando os de `yolo_models/` da raiz) estão no git sem LFS.
- `legado/database/tcc-0SF/YOLO_dataset/validation/labels.cache` está commitado.
- **Sugestão:** usar Git LFS ou armazenamento externo e redimensionar as imagens para cerca de 1280 px. Isso não altera o resultado com `imgsz=640`.

### E5. Sem configuração centralizada nem código compartilhado

- `PORT = "COM5"`, caminhos de modelo, ângulos e `CONF` estão repetidos em 6 arquivos.
- As funções `send_line` e `read_reply` foram copiadas 3 vezes.
- O mapeamento das 6 classes aparece em 3 lugares: `val.py`, `example_integration_ultralytics.py` e `middleware_gui.py`.
- Não há `requirements.txt`, embora o README do middleware cite um.

---

## 🟡 Moderado

### M1. `legado/scripts/val.py:59`: métricas por classe com rótulos trocados ⚠️ afeta os resultados do TCC

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
- ✅ **A monografia não é afetada:** ela só usa `mean_precision` (Tabela `tab:bench-cenarios`), que é uma média e não depende da ordem. A planilha continua errada se for usada em outro lugar.

### M2. `legado/scripts/model_2.py:144`: um mesmo objeto aciona o servo várias vezes

- O debounce (`DETECTION_COOLDOWN`) é global e baseado só em tempo.
- Quando um objeto é detectado na ROI a esteira **para**, e o objeto continua parado dentro da ROI.
- Durante os ~5,5 s de atuação ele é enfileirado de novo a cada 1 s, o que gera 4 ou 5 acionamentos fantasmas.
- **Correção:** usar tracking (`model.track` com IDs) ou ignorar detecções enquanto `processing=True`.

### M3. `legado/scripts/model_2.py`: a geometria entre câmera e desviador não é considerada

- O servo atua no instante em que o objeto cruza a ROI, e a esteira para nesse mesmo momento.
- ❓ O desviador fica logo abaixo da câmera? Se estiver mais adiante, falta um atraso de transporte (distância ÷ velocidade).

### M4. `legado/scripts/model.py:61`: o filtro de ângulo repetido descarta objetos

- `if angle != last_angle_sent` faz com que dois plásticos seguidos acionem só o primeiro.
- Também não há ROI: dispara assim que o objeto aparece em qualquer parte do frame.

### M5. Middleware: o acionamento não depende da posição do objeto

- Enquanto o objeto estiver visível, a GUI envia um `PULSE` a cada 300 ms de cooldown.
- No firmware, `delay(ms)` (`esp32_cancela.ino:28`) bloqueia o loop. Os pulsos se acumulam no buffer serial e continuam sendo executados depois que o objeto já passou.

### M6. `legado/database/*/YOLO_dataset/data.yaml`: `path:` absoluto do Windows

- O caminho `C:/Users/vitor/Documents/...` faz `val.py` e `test-yolo-format.py` falharem em qualquer outra máquina.
- **Correção:** remover o `path:` ou torná-lo relativo.

### M7. `legado/scripts/convert-to-yolo-format.py` está quebrado

- O caminho `../datasets/45-SF/45-SF.json` não existe.
- `labels_dir` espera um diretório, não um arquivo.
- O padrão `cls91to80=True` remapearia os IDs das classes.
- Os labels atuais estão corretos (IDs TACO e polígonos), então a conversão foi feita de outro jeito.
- ✅ **Resolvido pela monografia:** a anotação e a exportação foram feitas no Roboflow. O script está obsoleto e pode ser removido.

---

## 🟢 Pontual

| # | Local | Problema |
|---|---|---|
| P1 | `legado/scripts/final_model.py:13-17` | `MODEL_SOURCE` é definido duas vezes. `USE_WEBCAM` não é usado. A inferência roda em `IMG`, um caminho `C:\Users\natha\...`, e não na webcam. |
| P2 | `legado/scripts/final_model.py:44-50` | O ramo `glass` não envia nada mas chama `readline()` mesmo assim. `sleep(5)` bloqueia o stream a cada detecção. A serial é aberta no nível do módulo com `sleep(10)`. |
| P3 | `legado/scripts/model.py:52` | `save=True` na webcam grava vídeo continuamente em `runs/`. |
| P4 | `middleware_gui.py:239,252` | Se o usuário digitar algo não numérico num Spinbox, `.get()` lança `TclError`. A exceção sai de `_poll_queue` antes do `root.after` (linha 227), e **a GUI para de processar detecções sem avisar**. |
| P5 | `middleware_gui.py:176` | Não espera o reset do ESP32 ao conectar, então os primeiros comandos podem se perder. Também nunca lê as respostas `OK ...`. |
| P6 | `esp32_cancela.ino:82` | `inbuf` cresce sem limite se nunca chegar `\n`. |
| P7 | `legado/yolo_models/yolo11.py:3` | O caminho `./yolo/yolo11n.pt` não existe. O arquivo está em `legado/yolo_models/yolo11n.pt`. |
| P8 | `legado/scripts/test-yolo-format.py` | Imprime "base 1" fixo. Na prática duplica o `val.py`. |
| P9 | `legado/interface/canva/interface.html:793` | Tem um script injetado do Cloudflare (`/cdn-cgi/challenge-platform`), sobra da exportação, que deve ser removido. |
| P10 | `legado/scripts/model_2.py` | Os atalhos de teclado só funcionam no Windows (`msvcrt`). |
| P11 | `.gitignore` | Falta `*.cache` e `.venv/` (o `.gitignore` da raiz já cobre `__pycache__/` e `venv`). |

---

## Monografia (fonte Overleaf)

Referências no formato `CapN:linha` dos arquivos em `tcc2025/`. Não foi possível compilar localmente (falta o pacote `textcase.sty`), então os itens de LaTeX vêm de análise estática.

### 🔴 T1. O sistema descrito no texto não está no repositório

- Cap5:18-21 e 81-83 descrevem um frontend React/Vite/Tailwind com WebSocket e um backend com `YOLOPipeline`, `SerialController` e `SystemState`. Nada disso existe aqui.
- Também faltam os pesos do YOLOv8s com fine-tuning e o firmware do servo/motor.
- A Figura `fig:esteira_funcionando` mostra metal, plástico e papel sendo separados. Com o mapeamento por substring deste repo (E2), metal (`Drink can`) e papel nunca seriam reconhecidos, o que confirma que a demo usou outro código.
- ❓ Onde está esse código? Para a banca e para reprodutibilidade, vale versioná-lo e citar o repositório no texto.
- ✅ **Resolvido pela versão final:** frontend, backend, firmware e pesos estão na raiz deste repositório. Resta uma divergência: o backend (`backend/ecovision_local_modf.py`) é um arquivo de funções, e só `SystemState` é classe. `YOLOPipeline` e `SerialController` existem apenas no diagrama de `docs/diagrams/` e no texto.

### 🔴 T2. A avaliação do fine-tuning provavelmente tem vazamento de dados

- Os 4 cenários fotografam **as mesmas cenas** com segundos de diferença (ex.: `45CF 14:18:21`, `0CF 14:18:29`, `0SF 14:18:39`, `45SF 14:18:49`). São a mesma disposição de objetos, só com ângulo ou flash diferentes.
- Cap5:182-184: o fine-tuning usou "a mesma base de dados" (~100 imagens) com split aleatório 80/20. Assim, quase certamente há a mesma cena no treino e na validação, o que deixa os valores de precisão ~0,78 e mAP50 ~0,80 **otimistas**. A validação também tem só ~18-20 imagens.
- Cap5:214 compara esse mAP50 com o dos modelos pré-treinados, mas estes foram avaliados na base inteira (incluindo as imagens que depois viraram treino), e a tabela de mAP pré-treinado está comentada (Cap5:149-162). O leitor não tem a linha de base.
- **Correção:** dividir treino e validação **por cena** (agrupando as 4 fotos da mesma cena), retreinar e reavaliar. Se não houver tempo, declarar a limitação explicitamente.
- ❓ Como o split foi feito: aleatório por imagem no Roboflow?

### 🟡 T3. A métrica "Precisão Média" da Tabela `tab:bench-cenarios` é enganosa

- Os valores vêm de `metrics.box.mp` (batem com a planilha). No Ultralytics, isso é a precisão por classe **no limiar de confiança que maximiza o F1**, avaliada com `conf=0.001`. Não é "a proporção de predições corretas" no limiar de operação (0,4), como diz Cap5:147.
- Classes sem nenhuma detecção correta aparecem com P = 1,0 e R = 0 e **inflam a média**. Exemplos: YOLOv8n 0SF (67,63%) tem 2 das 6 classes nessa situação, e YOLOv8s 45SF (76,98%) tem 1.
- Escolher o modelo só pela precisão ignora o recall, que é ~0 em algumas classes.
- **Correção:** reportar mAP@0.5 (a tabela comentada em Cap5:149-162; o YOLOv8s continua vencendo, então a conclusão se mantém) e/ou P e R juntos.

### 🟡 T4. O texto e o código divergem na lógica de controle da esteira

- Cap4:89 diz que a velocidade é mantida constante, e Cap5:120,127 fala em regular a velocidade pela ponte H. O código só tem `MOTOR ON` e `MOTOR OFF`, e o `model_2.py` **para** a esteira a cada detecção.
- A limitação "separação descompassada" (Cap5:307) só faz sentido com a esteira em movimento contínuo.
- As limitações "múltiplas detecções" e "separação descompassada" (Cap5:305-309) são exatamente M2 e M3. Os trabalhos futuros (Cap6) falam só de dataset e hardware. Vale citar as soluções de software: tracking com IDs e contagem por cruzamento de linha, e compensação de atraso por distância/velocidade.
- ✅ **Resolvido pela versão final:** a esteira se move continuamente. O backend não para o motor na detecção, e o firmware usa PWM fixo (255), sem regulação de velocidade. Isso é coerente com Cap4:89 e Cap5:307, mas não com Cap5:120,127.

### 🟡 T5. Os critérios de aceitação citados não existem mais, e falta resultado quantitativo do sistema

- Cap4:297 afirma que a viabilidade foi "garantida pelo cumprimento dos requisitos [...] taxa mínima de acerto [...] tempo máximo de resposta". Porém os critérios numéricos foram comentados (RF01: 40%; RF03: 10% e < 1 s), e nenhum tempo de resposta é medido.
- Cap5:137 anuncia testes em cinco níveis (modelo, software, hardware, sistema completo e validação geral), mas só há subseções de modelo, software e sistema completo, sem números.
- Cap6:327 conclui que tudo funcionou "corretamente", mas nenhum dado sustenta isso, e as limitações relatam acionamentos indevidos.
- **Sugestão:** passar N objetos de cada material pela esteira e reportar a taxa de separação correta por material e a latência entre detecção e atuação.

### 🟢 Pontuais

| # | Local | Problema |
|---|---|---|
| T6 | Cap1:43, Cap4:89,104 vs Cap5:11,238 | Os materiais aparecem como "papelão" em um lugar e "papel" em outro, mas o dataset tem os dois (`normal paper` e `corrugated carton`). Uniformizar. |
| T7 | Cap4:301 | "64 subgrupos" do TACO. O TACO tem 60 categorias (o `data.yaml` tem 60 + `Background`). Conferir com `TACO_TAXONOMY`. |
| T8 | Cap2:132 | "otimiza apenas suas camadas finais": o Ultralytics treina todas as camadas, a menos que se use `freeze`. ❓ Foi usado `freeze`? |
| T9 | Cap1:58 | `\cite{Evreka_2025}`, mas a chave no `refs.bib` é `EVREKA_2025`. O BibTeX pode acusar *case mismatch* e a citação sair como "?". Conferir no PDF. |
| T10 | Cap5:28,111 vs Cap4:265 | O texto fala em "uma ponte H", e a tabela de custos lista 2 módulos L298N. |
| T11 | Cap4:118-136,178 | RF02, RF03, RF04 e RNF03 falam em "cancelas" (plural), mas o sistema tem um único servo. |
| T12 | `main.tex:543` | O capítulo "Método de Trabalho" (Cap3) está comentado e o conteúdo dele foi duplicado no Cap4. ❓ É intencional? O modelo da Poli prevê esse capítulo. |

---

## Dúvidas em aberto

1. **Geometria:** qual é a distância entre a câmera e o servo, e qual a velocidade da esteira? (M3, T4)
2. **Fine-tuning:** o split foi aleatório por imagem? Usou `freeze`? (T2, T8)
3. **Capítulo de Método:** a remoção foi intencional? (T12)
4. **M1:** confirmar com `print(metrics.box.ap_class_index)`.
5. **Citação Evreka:** ela aparece corretamente no PDF? (T9)

Respondidas pela monografia: hardware real (E1), CF/SF = **com/sem flash**, fine-tuning realizado (E3), anotação no Roboflow (M7).

Respondidas pela versão final: o código final está na raiz deste repositório (T1); a esteira se move continuamente (T4); o fine-tuning usou as classes TACO (61 = 60 + `Background`), não 4 materiais (veja [`yolo_models/README.md`](yolo_models/README.md)).

## Prioridade sugerida

**Monografia:**

1. **T2:** o principal resultado quantitativo pode estar inflado.
2. **T5:** falta resultado do sistema completo, o que a banca tende a cobrar.
3. **T3:** trocar ou complementar a métrica. A conclusão se mantém.
4. **T6–T12:** correções rápidas de texto.

**Código de `legado/`:** M1, se a planilha for reaproveitada. Os demais itens (E2, M2...) já não importam, porque o desenvolvimento segue na versão final da raiz. Os problemas dela estão no [`README.md`](README.md#limitações-conhecidas).
