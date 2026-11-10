# Objetivo — ciclo de melhoria do detector da esteira

O sistema completo que este repositório persegue: as imagens da própria esteira viram base de treino e de teste do YOLO, com anotação automática por voto entre modelos e revisão humana só onde ela é necessária. Requisitos na monografia preliminar (`docs/ecovision-iterativo-prelim.pdf`): RF11 a RF14, RNF08, seções 5.3.2 (taxonomia), 5.3.4 (viés de automação) e 5.3.5 (divisão dos dados). Fluxo desenhado em `docs/diagrams/diagrama_v3.drawio`.

**Escopo atual**: só o **framework de anotação** (anotadores intercambiáveis que gravam propostas) e a **página de visualização, correção e edição** dos resultados, planejados em [`anotacao/PLANO-REVISAO.md`](anotacao/PLANO-REVISAO.md) (tarefa T1). Os demais passos do fluxo estão nas [tarefas](#tarefas), com o que já foi decidido sobre eles.

**Status**: `[ ]` pendente · `[x]` feito (com hash) · `[~]` parcial

## 1. Fluxo (diagrama v3)

```
esteira → YOLO → banco (imagens + logs) → treino ou teste? (por lote, 1 em cada 5 para o teste)
  treino → 3 anotadores (em lote, no dia seguinte) → voto 3oo3
             passou     → base de treino (caixas de consenso)
             não passou → revisão humana → base de treino (caixas corrigidas)
             (+ auditoria: 5% das aprovadas também vão à revisão)
           base de treino → fine-tuning do YOLO
  teste  → segmentação sem classe (união das caixas dos 3 anotadores)
           → revisão humana obrigatória → base de teste → avaliação do YOLO (com a base externa)
```

O código do voto aceita N anotadores, mas cada um a mais custa uma integração e baixa a taxa de aprovação.

## 2. Estado de cada imagem

O framework (T1) grava as propostas de cada anotador separadas das anotações finais, e um `imagens.csv` com o status de cada imagem. O sistema completo acrescenta colunas a esse arquivo, que continua sendo a fonte do estado:

- `lote`: sessão de captura de onde a imagem veio.
- `conjunto`: `treino` ou `teste`, sorteado por lote na entrada e nunca mais alterado.
- `voto`: `passou`, `falhou` ou vazio (teste, ou ainda não votada); `motivo` diz por que falhou (contagem diferente, classe diferente, IoU baixo, imagem vazia).
- `status`: além de `pendente`, `revisada` e `descartada` (do framework), `aprovada` (voto, sem humano).

`treino.txt` recebe as de treino `aprovada` ou `revisada`; `teste.txt`, só as de teste `revisada`. Uma imagem sem `labels/` nunca entra em nenhum dos dois. O `data.yaml` aponta para os dois arquivos.

Por que as propostas não vão direto para `labels/`: o Ultralytics trata imagem sem objetos como fundo, então uma imagem não revisada, ou com objetos que o modelo não achou, entraria no treino como negativo falso; e sem guardar a proposta original não dá para medir a precisão de cada anotador (RF13).

## 3. Voto 3oo3

Cada anotador entrega suas caixas já filtradas pelo próprio limiar e pelo NMS, com as classes do `classes.yaml`. O `votar.py` casa as caixas dos três:

1. Casamento guloso pelo IoU, entre caixas da mesma classe, com IoU ≥ 0,5 (`--iou`).
2. **Passa** se toda caixa de cada anotador casou com uma caixa de cada um dos outros dois: mesma quantidade de objetos, mesmas classes, posições próximas.
3. **Imagem vazia** (nenhum anotador achou nada) não passa e vai à revisão: na esteira quase toda imagem tem objeto, e um negativo falso no treino é o erro mais caro (seção 2).
4. **Caixa de consenso**: a mediana de cada coordenada entre as três; a confiança é a menor das três (serve para ordenar a fila de revisão, RF10).

**Risco: erros correlacionados.** Três modelos que erram igual aprovam o erro. Hoje o Grounding DINO confunde PET com vidro, e um classificador do mesmo tipo tende a confundir também. Mitigações:

- **Anotadores de famílias diferentes** (seção 5). A híbrida Grounding DINO + SigLIP usa as caixas do Grounding DINO; ela e o Grounding DINO puro não contam como dois votos independentes na localização.
- **Medir antes de adotar**: o `avaliar.py` ganha o modo `--voto`, que dá a taxa de aprovação e a fração das imagens aprovadas que estão corretas por inteiro frente aos rótulos da equipe.
- **Auditoria**: uma amostra aleatória das aprovadas (ex.: 5%) vai para a fila de revisão sem que o revisor saiba que foi aprovada. Ela estima o erro das aprovadas durante o uso (RF13).

## 4. Viés de automação no teste

O framework terá o modo "sem pré-anotação" (o revisor anota do zero), que mede o viés e dá o tempo de anotação manual, a linha de base do ganho.

Pesa mais no teste: se o revisor parte das propostas dos anotadores, o viés vai para a base que mede o YOLO e os próprios anotadores. Por isso o teste chega **segmentado e sem classe** (decisão 5):

- As caixas são a união das caixas dos três anotadores, com as sobrepostas (IoU ≥ 0,5) fundidas numa só. A união favorece o recall: sobra caixa para remover, falta pouca para desenhar.
- A página não mostra classe, confiança nem quem propôs. O revisor só seleciona cada caixa, dá a classe (`1`–`9`) e ajusta, remove ou acrescenta caixas.
- Sem classe proposta, a classe do teste não herda o viés. A localização ainda herda um pouco; o registro guarda quantas caixas foram ajustadas, removidas e acrescentadas, o que mede esse resto.

## 5. Escolha dos anotadores

Com o voto, a pergunta deixa de ser qual é o melhor anotador e passa a ser **que trio, quando concorda, quase nunca erra, e concorda com frequência suficiente** para poupar revisão. Um anotador preciso mas muito parecido com outro vale menos que um mais fraco de outra família. Primeiro trio a medir: Grounding DINO, OWLv2 e YOLOE; a híbrida com SigLIP entra no lugar do Grounding DINO puro se corrigir a classe. Na GTX 1650 os três não cabem juntos: o `anotar.py` roda um anotador por vez sobre o lote inteiro.

Nas fotos testadas, o Grounding DINO localiza bem e erra a classe; por isso entram também opções que só **reclassificam** as caixas. Custo = esforço para encaixar no `anotar.py` (a classe `Anotador` já isola o modelo).

| Opção | Como entra | Licença | GTX 1650 (4 GB) | Custo | Observações |
|---|---|---|---|---|---|
| Grounding DINO tiny/base (atual) | — | Apache 2.0 | Cabe | — | Referência de precisão para rótulos offline |
| OWLv2 | `transformers`, mesma API; pontuação por texto de classe (dispensa o mapeamento por token) | Apache 2.0 | Cabe | ~½ dia | Concorrente mais direto |
| YOLO-World / YOLOE | `ultralytics` (`set_classes`) | GPL-3.0 / AGPL-3.0 | Tempo real | ~½ dia | Mais rápidos, menos precisos; o YOLOE treina como YOLO comum e poderia virar o detector da esteira |
| Grounding DINO + SAM 2 | Caixas do DINO como prompt do SAM | Apache 2.0 | Cabe (SAM 2 pequeno) | ~1 dia | Melhora caixas, não a classe |
| SAM 3 (texto → máscaras e caixas) | `ultralytics` ≥ 8.3.237 (`SAM3SemanticPredictor`) ou `transformers` | Licença própria da Meta (verificar) | Provavelmente apertado (~850M parâmetros) | ~1–2 dias | Pesos baixados à mão |
| Florence-2 | `transformers` com `trust_remote_code` | MIT | Cabe | ~1 dia | Sem confiança por caixa: quebra a ordenação por incerteza (RF10) |
| VLM local (Qwen2.5-VL/Qwen3-VL 3B–7B) | Caixas em JSON na resposta | Apache 2.0 (maioria) | 3B quantizado cabe; 7B não | ~2–3 dias | Lento, sem confiança calibrada; bom para decidir material |
| APIs (Gemini, DINO-X / Grounding DINO 1.6 Pro) | HTTP | Comercial, por imagem | — | ½–1 dia | Imagens saem da máquina (RNF09/LGPD) |
| Detector próprio (`best.pt` e retreinos) | `ultralytics` | AGPL-3.0 | Cabe | Baixo | Aprendizado ativo clássico; herda os próprios erros; para os ciclos seguintes |

**Híbrida (hipótese a testar)**: manter as caixas do Grounding DINO e reclassificar cada recorte com SigLIP ou CLIP (`transformers`, Apache 2.0, ~½–1 dia), que compara o recorte com textos como "clear plastic bottle" e "glass bottle". Um VLM pode ser chamado só nos recortes ambíguos.

**Como escolher**: `anotacao/avaliar.py` mede cada candidato (acerto de classe e de material com as caixas verdadeiras; precisão e recall por limiar de confiança) nas fotos de `legado/database/*/YOLO_dataset/validation`, que têm rótulos da equipe nas mesmas 6 classes do `classes.yaml` (polígonos de 4 pontos → caixas). Ressalvas: fotos paradas, sem esteira; o vazamento entre os cenários não pesa, porque nenhum candidato treinou nelas. O script serve à monografia (objetivo 3) e é reaproveitado a cada ciclo.

**Ordem**: (1) `avaliar.py` com o Grounding DINO como linha de base; (2) OWLv2 e YOLOE; (3) híbrida com SigLIP; (4) `avaliar.py --voto` com o trio; (5) SAM 2/3 só se as caixas virarem o problema.

**Critério do trio** (a confirmar com os números): ao menos 95% das imagens aprovadas corretas por inteiro. A taxa de aprovação decide se o voto compensa: abaixo de uns 30%, quase tudo vai ao revisor de qualquer jeito.

### Linha de base (2026-10-27)

`avaliar.py` com o Grounding DINO `tiny` nas 88 fotos de validação (375 caixas):

- **Localização**: toda caixa verdadeira tem uma consulta do modelo com IoU ≥ 0,5.
- **Classe**: 46% de acerto com a caixa já localizada; material, 50%. `Glass bottle` acerta 7%: vira `Clear plastic bottle` (33) ou `Drink can` (30). `Clear plastic bottle` vira `Glass bottle` em 29 de 58.
- **Detecção**: no limiar padrão 0,35, precisão 0,39 e recall 0,33.
- **Hipótese descartada**: pontuar a classe pela média dos tokens do prompt, e não pelo máximo, para que a palavra comum ("bottle") não decida por todas. A classe foi a 47% (de 46%) e o recall em 0,35 caiu para 0,21. A confusão não vem do texto compartilhado: o modelo não separa os materiais.

Conclusão: manter o Grounding DINO para as caixas e trocar quem decide a classe. A híbrida com SigLIP passa à frente de OWLv2 e YOLOE.

### Verificação das classes e do teste (2026-10-27)

- **Rótulo `Glass bottle` não corresponde aos objetos.** Nenhuma das 97 caixas é garrafa de vidro: são copos, taças, potes e tigelas de vidro, e 3 são latas rotuladas errado (tcc-0SF 140322 e outra foto). A equipe usou `Glass bottle` para todo vidro. Os 7% medem a escolha da classe, não o modelo. As outras classes conferem, com mistura: `Plastic bottle cap` inclui tampas de pote, e `Corrugated carton` inclui caixas finas de papel-cartão impresso.
- **Prompt bem formado.** Cada palavra vira um token inteiro, o mapa token → classe está certo, e o `" . "` é o separador que o modelo usa para codificar cada frase em separado (`generate_masks_with_special_tokens_and_transfer_map`).
- **Vocabulário amplo** (59 classes TACO e 27 termos genéricos, em 2 blocos): os nomes vencedores conferem com os objetos. Vidro sai como "disposable plastic cup", "glass bowl", "cup", "wine glass" e "drinking glass", nunca "glass bottle". O material dos copos transparentes continua ambíguo. Lata sai como "soda can", tampa como "bottle cap", papel como "crumpled paper". Ressalvas: o teste é qualitativo, porque as pontuações entre frases não são calibradas; frases TACO com substantivo genérico ("squeezable tube", "disposable food container") vencem sem sentido; parte dos termos genéricos foi escolhida depois de ver os recortes.
- **Prompt que descreve o objeto real.** Só `Glass bottle` → "drinking glass": vidro de 7% para 38%, classe 46% → 55%, material 50% → 60%; detecção em 0,35, precisão 0,39 → 0,56 e recall 0,33 → 0,48. Trocar também tampa, lata e papel pelos vencedores do vocabulário amplo dá 57% e 62%, mas lata e papel pioram. O vencedor do teste qualitativo não é necessariamente o melhor prompt, e diferenças de 2 pontos são ruído: as 4 validações são as mesmas cenas, e os prompts foram ajustados nelas.

Antes do SigLIP:
1. ~~Decidir a taxonomia do vidro~~: decidido (decisão 8), três classes. Falta levá-las ao `classes.yaml` junto com as correções do item 3, para o `avaliar.py` não comparar as classes novas com rótulos `Glass bottle`.
2. Permitir mais de um prompt por classe, com a pontuação máxima entre eles: um prompt não cobre copo, pote e tigela.
3. Registrar as correções dos rótulos da equipe num arquivo em `anotacao/`, sem editar `legado/`.
4. Refazer a linha de base. O SigLIP herda o mesmo cuidado: as descrições têm de corresponder aos objetos das fotos, não ao nome TACO.

### Plano: SigLIP como classificador no `avaliar.py`

**Objetivo**: medir se reclassificar o recorte de cada caixa com o SigLIP supera a classe do Grounding DINO (46% de classe, 50% de material) e, se superar, levar a troca ao `anotar.py`.

**Modelos** (`transformers`, Apache 2.0, todos cabem na GTX 1650 em fp16 e com folga na T4):

| Modelo | Por quê |
|---|---|
| `google/siglip2-base-patch16-224` | Ponto de partida: pequeno e rápido |
| `google/siglip2-so400m-patch14-384` | Maior e com mais resolução; transparência e espessura do material são detalhe fino |
| `openai/clip-vit-large-patch14` | Controle: diz se a diferença vem do SigLIP ou de qualquer modelo de imagem e texto |

**Código**:

1. `anotacao/classificador.py`, com `Classificador(classes, modelo, dispositivo)` e o método `classificar(imagem, caixas) -> [(classe ou None, confianca)]`. Os recortes de uma imagem vão num lote só. Os embeddings dos textos são calculados uma vez no construtor. O mesmo módulo serve depois ao `anotar.py`.
2. **Recorte**: a caixa com margem (`--margem`, padrão 10%), porque o contexto ajuda (a tampa está na garrafa), completada até ficar quadrada com cinza. O processador do SigLIP redimensiona para quadrado e achataria garrafas, que são compridas. Funções puras, testáveis sem o modelo.
3. **Textos por classe**: um campo opcional `descricoes` no `classes.yaml`, uma lista de frases visuais (ex.: `Glass bottle`: "a thick rigid glass bottle", "a green or brown glass bottle"; `Clear plastic bottle`: "a thin crinkled transparent PET plastic bottle"). Sem `descricoes`, o texto usado é o `prompt`. Cada frase passa por modelos como "a photo of {}" e "{} on a conveyor belt", e a classe recebe a média dos embeddings. O `classes.yaml` continua sendo a fonte única (decisão pendente 2).
4. **Distratores**: uma lista `distratores` no `classes.yaml` ("a glass cup", "a glass jar", "a plastic cup", "an empty conveyor belt"), que entram na comparação e, se vencerem, dão classe `None` (descartar). Na avaliação por caixa verdadeira, `None` conta como erro. Na detecção, é o que pode reduzir os falsos positivos.
5. **Confiança**: o SigLIP pontua cada par imagem-texto com sigmoide, de forma independente. Para escolher a classe vale o maior logit. A confiança é o softmax dos logits das classes, com a escala do modelo, para que a ordenação por incerteza (RF10) continue possível.
6. **`avaliar.py`**: opção `--classificador MODELO` (repetível). Cada classificador ganha sua matriz de confusão, ao lado da do Grounding DINO, sobre as mesmas caixas verdadeiras. Na detecção, uma linha "híbrida" por limiar: caixas filtradas pelo Grounding DINO (a confiança dele como objetividade, o NMS já ignora a classe), classe do SigLIP, `None` removida. Mostrar também o tempo por recorte.

**Experimentos**, todos com as mesmas 375 caixas:

| # | Configuração | Pergunta |
|---|---|---|
| 1 | SigLIP2 base, só o `prompt` | O recorte sozinho já resolve? |
| 2 | + `descricoes` | Descrever o material ajuda? |
| 3 | + distratores | Quanto custa na classe e quanto ganha na detecção? |
| 4 | so400m e CLIP-L com a melhor configuração | Tamanho e família do modelo |
| 5 | margem 0, 10 e 25% | Contexto em volta do objeto |

**Risco: ajustar as descrições às fotos de validação.** Não há conjunto independente: `tcc-teste` não tem rótulos, e as quatro validações são as mesmas cenas. Mitigações:
- poucas iterações de texto, todas registradas aqui com o resultado;
- ajustar com as fotos de 0° (`tcc-0CF`, `tcc-0SF`) e conferir nas de 45°, sabendo que as cenas se repetem;
- confirmar nas primeiras fotos da esteira assim que existirem.

**Decisão**: levar o SigLIP ao `anotar.py` (opção `--classificador`) se ele subir bem o acerto de material, por exemplo em 15 pontos ou mais, e tirar `Glass bottle` dos 7%. Se o zero-shot não separar PET de vidro, o passo seguinte reaproveita os mesmos recortes e embeddings: kNN ou regressão logística sobre as caixas da equipe. A validação desse passo precisa ser por cena, não por cenário. Agrupar as fotos dos quatro cenários por cena (horário e conteúdo) é pré-requisito.

**Esforço**: ~½ dia para o `classificador.py` e a integração ao `avaliar.py`, ~½ dia para os experimentos.

Fontes: [SAM 3 — Ultralytics](https://docs.ultralytics.com/models/sam-3), [Ultralytics 8.3.237](https://newreleases.io/project/pypi/ultralytics/release/8.3.237), [SAM 3 — Transformers](https://huggingface.co/docs/transformers/model_doc/sam3), [Grounding DINO vs YOLOE — Roboflow](https://playground.roboflow.com/models/compare/grounding-dino-vs-yoloe), [Open-vocabulary detection — Fora Soft](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/open-vocabulary-detection-grounding-dino-florence-2-rtdetr-rfdetr). Levantamento de 2026-10-27; custos e cabimento na GPU são estimativas, não medidos.

## Tarefas

| # | Status | Tarefa | Depende de | Verificação |
|---|---|---|---|---|
| T1 | [~] | **Framework de anotação e página de revisão** (escopo atual): anotadores intercambiáveis gravando propostas, página para ver, corrigir e editar, registro da revisão. Plano: [`anotacao/PLANO-REVISAO.md`](anotacao/PLANO-REVISAO.md) | — | as do plano |
| T2 | [~] `b70ac8a` | **Escolha dos anotadores** (seção 5): linha de base do Grounding DINO feita; faltam as pendências antes do SigLIP (taxonomia do vidro, vários prompts por classe, correções dos rótulos da equipe, nova linha de base), a híbrida com SigLIP, OWLv2 e YOLOE como anotadores do T1 | T1 (interface de anotador) | tabelas do `avaliar.py` |
| T3 | [ ] | **`avaliar.py --voto`**: taxa de aprovação e fração das aprovadas corretas por inteiro, para escolher o trio | T2 | pytest com caixas sintéticas; tabelas |
| T4 | [ ] | **Captura na esteira**: o backend grava imagens e logs por lote (banco do diagrama) | — | teste com a esteira |
| T5 | [ ] | **Entrada por lote**: importa um lote para `imagens.csv` com `lote` e o sorteio treino/teste (1 lote em 5) | T1, T4 | pytest |
| T6 | [ ] | **`votar.py`**: aplica o 3oo3 (seção 3), grava `labels/` das aprovadas com as caixas de consenso, `voto`/`motivo`, `treino.txt`, `teste.txt` e `data.yaml` | T1, T3 | pytest do voto com caixas sintéticas |
| T7 | [ ] | **Revisão do voto na página**: fila só das `falhou`; caixas de consenso e, separadas, as que só um ou dois propuseram, com quem propôs | T1, T6 | pytest da API; teste manual |
| T8 | [ ] | **Auditoria**: amostra das aprovadas (ex.: 5%) na fila de revisão, sem o revisor saber | T6, T7 | pytest |
| T9 | [ ] | **Modo de teste**: segmentado e sem classe (padrão no teste, seção 4) e sem pré-anotação | T1, T5 | pytest; teste manual |
| T10 | [ ] | **`metricas.py`** (RF13): taxa de aprovação e motivos, erro das aprovadas pela auditoria, precisão e recall de cada anotador frente à revisão, tempo por imagem e por objeto, taxa de cada tipo de correção | T1, T6, T8 | pytest com registros sintéticos |
| T11 | [ ] | **Novas classes pela página** (RF14): acrescenta no fim do `classes.yaml` e regenera o `data.yaml` | T1 | pytest; teste manual |
| T12 | [ ] | **Fine-tuning do YOLO** com a base de treino; versões fixadas antes (RNF07) | T6, T7 | métricas do treino |
| T13 | [ ] | **Avaliação do YOLO** com a base de teste e uma base externa | T9, T12 | métricas por classe e material |

## Decisões do sistema

As decisões que só valem para o framework (ferramenta própria, fonte das classes, um revisor) ficam no plano do T1. Os números são os do plano original.

| # | Questão | Decisão |
|---|---|---|
| 4 | ~~Um anotador ou vários?~~ | **Decidido (2026-10-28)**: três anotadores com voto 3oo3; quem não passa vai à revisão humana (seção 3). |
| 5 | ~~O teste chega ao revisor com as propostas dos anotadores ou sem elas?~~ | **Decidido (2026-10-28)**: segmentado e sem classe. Os objetos chegam delimitados para poupar a seleção; a classe é do revisor (seção 4). |
| 6 | ~~O voto exige a mesma classe ou só o mesmo material?~~ | **Decidido (2026-10-28)**: mesma classe. Por material aprovaria mais, mas a imagem ficaria sem classe definida para o treino. |
| 7 | ~~Proporção treino/teste e unidade do sorteio~~ | **Decidido (2026-10-28)**: sorteio por lote de captura, 1 lote em cada 5 para o teste. Frames seguidos da esteira são quase iguais; sortear imagem a imagem vazaria cenas entre os conjuntos. |
| 8 | ~~Taxonomia do vidro~~ | **Decidido (2026-11-09)**: três classes TACO, `Glass bottle`, `Glass jar` e `Glass cup` (copos, taças e tigelas). `Glass jar` e `Glass cup` entram no fim do `classes.yaml`, para não mudar os ids. |
