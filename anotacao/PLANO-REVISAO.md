# Plano — anotação por voto entre modelos e revisão humana

Branch de origem: `feature/anotacao-assistida` (`3084516`). Requisitos da monografia (`docs/ecovision-iterativo-prelim.pdf`): RF12 (revisar), RF13 (tempo e correções), RF14 (novas classes), RNF08 (usabilidade), seção 5.3.4 (viés de automação). Fluxo: `docs/diagrams/diagrama_v3.drawio`.

**Status**: `[ ]` pendente · `[x]` feito (com hash) · `[~]` parcial

**Ponto de partida**: o `anotar.py` grava as propostas do Grounding DINO direto em `labels/`, e o `visualizar.py` gera uma página estática (`file://`, só leitura) com as caixas. A ideia é evoluir essa página para uma de revisão, servida por um servidor Python local que lê as propostas e grava as anotações corrigidas.

**Mudança de 2026-10-28**: em vez de um anotador cujas propostas são todas revisadas, três anotadores votam. Se os três concordam (voto 3oo3), a imagem entra no treino sem revisão; se não, vai para a fila de revisão humana. As imagens de teste são sempre revisadas.

---

## 0. Fluxo (diagrama v3)

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

O diagrama foi atualizado com as decisões de 2026-10-28. A base externa e a avaliação do YOLO ficam fora deste plano, que cobre do banco até as duas bases. O código do voto aceita N anotadores, mas cada um a mais custa uma integração e baixa a taxa de aprovação.

## 1. Separar proposta, voto e anotação final (decisão prévia)

Problemas de gravar as propostas em `labels/`:

- O Ultralytics trata imagem sem objetos como fundo: uma imagem não revisada, ou com objetos que o modelo não achou, entraria no treino como negativo falso.
- Sem guardar a proposta original, não dá para medir a precisão de cada anotador (RF13).

Estrutura proposta:

```
anotacoes/
├── images/
├── propostas/<anotador>/<nome>.json  # saída de cada anotador: classe, confiança, caixa (imutável)
├── labels/<nome>.txt                 # caixas finais, formato YOLO: consenso do voto ou revisão
├── revisoes/<nome>.json              # registro da revisão: tempos e ação sobre cada caixa
├── imagens.csv                       # nome, lote, conjunto, voto, motivo, status
├── treino.txt, teste.txt             # gerados de imagens.csv; o data.yaml aponta para eles
└── data.yaml
```

`imagens.csv` é a fonte do estado, um arquivo só em vez de várias listas:

- `conjunto`: `treino` ou `teste`, sorteado por lote na entrada e nunca mais alterado.
- `voto`: `passou`, `falhou` ou vazio (teste, ou ainda não votada); `motivo` diz por que falhou (contagem diferente, classe diferente, IoU baixo, imagem vazia).
- `status`: `aprovada` (voto, sem humano), `pendente`, `revisada` ou `descartada`.

`treino.txt` recebe as de treino `aprovada` ou `revisada`; `teste.txt`, só as de teste `revisada`. Uma imagem sem `labels/` nunca entra em nenhum dos dois.

## 1a. Voto 3oo3

Cada anotador entrega suas caixas já filtradas pelo próprio limiar e pelo NMS, com as classes do `classes.yaml`. O `votar.py` casa as caixas dos três:

1. Casamento guloso pelo IoU, entre caixas da mesma classe, com IoU ≥ 0,5 (`--iou`).
2. **Passa** se toda caixa de cada anotador casou com uma caixa de cada um dos outros dois: mesma quantidade de objetos, mesmas classes, posições próximas.
3. **Imagem vazia** (nenhum anotador achou nada) não passa e vai à revisão: na esteira quase toda imagem tem objeto, e um negativo falso no treino é o erro mais caro (seção 1).
4. **Caixa de consenso**: a mediana de cada coordenada entre as três; a confiança é a menor das três (serve para ordenar a fila de revisão, RF10).

**Risco: erros correlacionados.** Três modelos que erram igual aprovam o erro. Hoje o Grounding DINO confunde PET com vidro, e um classificador do mesmo tipo tende a confundir também. Mitigações:

- **Anotadores de famílias diferentes** (seção 6). A híbrida Grounding DINO + SigLIP usa as caixas do Grounding DINO; ela e o Grounding DINO puro não contam como dois votos independentes na localização.
- **Medir antes de adotar**: o `avaliar.py` ganha o modo `--voto`, que dá a taxa de aprovação e a fração das imagens aprovadas que estão corretas por inteiro frente aos rótulos da equipe.
- **Auditoria**: uma amostra aleatória das aprovadas (ex.: 5%) vai para a fila de revisão sem que o revisor saiba que foi aprovada. Ela estima o erro das aprovadas durante o uso (RF13).

## 2. Arquitetura

- **Servidor**: `anotacao/revisar.py` com `http.server` da biblioteca padrão (`ThreadingHTTPServer`), só em `localhost`, sem dependência nova. Poucos endpoints e um revisor por vez não justificam um framework; se crescer (vários revisores, login), migrar para FastAPI.
- **Página**: HTML + JavaScript sem build, evoluindo do `visualizar.html`. Fica fora do `frontend/` da operação: papéis diferentes (revisor e operador) e pode rodar noutro computador (RNF05).
- **Gravações atômicas**: arquivo temporário e depois `os.replace`, para um Ctrl+C no meio não corromper um `.txt`.

| Método | Rota | Função |
|---|---|---|
| GET | `/api/imagens` | Lista com conjunto, status e menor confiança |
| GET | `/api/imagens/<nome>` | Caixas a revisar (consenso parcial ou propostas) e revisão atual, se houver |
| PUT | `/api/imagens/<nome>` | Grava as caixas finais, o registro e o status |
| GET | `/api/classes` | Classes |
| POST | `/api/classes` | Acrescenta uma classe no fim (RF14) |
| GET | `/images/<arquivo>` | A imagem |

## 3. Interações da página

O RNF08 pede revisão mais rápida que anotação manual: o fluxo comum deve caber em poucas teclas.

| Ação | Mouse | Teclado |
|---|---|---|
| Selecionar caixa | clique | `Tab` |
| Trocar a classe | menu na caixa | `1`–`9` |
| Remover caixa | botão | `Del` |
| Desenhar caixa nova | arrastar numa área vazia | `N` e depois arrastar |
| Ajustar ou mover caixa | alças nos cantos | — |
| Desfazer | — | `Ctrl+Z` |
| Salvar e ir para a próxima | botão | `Enter` |
| Descartar a imagem (inútil para treino) | botão | `D` |

Caixa proposta aparece tracejada e com a confiança; depois de tocada pelo revisor, fica contínua. A fila mostra só as `pendente`, com filtro por conjunto e ordem por confiança, para começar pelas incertas (RF10).

**O que o revisor vê numa imagem que não passou no voto**: as caixas em que os três concordaram e, separadas, as que só um ou dois propuseram, marcadas com quem propôs. Assim o revisor começa pelo ponto da discórdia, sem uma caixa duplicada por anotador.

## 4. Registro da revisão (RF13)

`revisoes/<nome>.json` guarda:

- **Tempo ativo**: o cronômetro pausa quando a aba perde o foco ou depois de 60 s sem interação.
- **Desfecho de cada caixa**: `aceita`, `classe_corrigida`, `caixa_ajustada` (IoU com a proposta abaixo de um limiar), `removida` ou `adicionada`.
- **Versões** dos anotadores e das classes que geraram as propostas.
- **Revisor**: campo já previsto, mesmo com um revisor só (ver decisão 3).

`anotacao/metricas.py` lê os registros e `imagens.csv` e calcula: taxa de aprovação pelo voto e motivos de falha; erro das aprovadas, pela auditoria; precisão e recall de cada anotador (casamento por IoU ≥ 0,5, com a revisão como referência); tempo médio por imagem e por objeto; taxa de cada tipo de correção.

## 5. Viés de automação (seção 5.3.4)

Marcação "sem pré-anotação" por imagem: o servidor esconde as propostas e o revisor anota do zero. Comparar com as revisadas mede o viés e dá o tempo de anotação manual, que é a linha de base do ganho.

Pesa mais no teste: se o revisor parte das propostas dos anotadores, o viés vai para a base que mede o YOLO e os próprios anotadores. Por isso o teste chega **segmentado e sem classe** (decisão 5):

- As caixas são a união das caixas dos três anotadores, com as sobrepostas (IoU ≥ 0,5) fundidas numa só. A união favorece o recall: sobra caixa para remover, falta pouca para desenhar.
- A página não mostra classe, confiança nem quem propôs. O revisor só seleciona cada caixa, dá a classe (`1`–`9`) e ajusta, remove ou acrescenta caixas.
- Sem classe proposta, a classe do teste não herda o viés. A localização ainda herda um pouco; o registro guarda quantas caixas foram ajustadas, removidas e acrescentadas, o que mede esse resto.

## 6. Escolha dos anotadores (antes da fase 1)

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
1. Decidir a taxonomia do vidro: `Glass cup` e `Glass jar` (TACO) ou uma classe só de vidro.
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

---

## Fases

A fase 0 define os anotadores e o critério do voto. As fases 1–3 já entregam o fluxo do diagrama com uma ferramenta usável (corrige classe e remove caixas erradas, os erros mais comuns hoje); 4–6 completam os requisitos.

| # | Status | Entrega | Verificação |
|---|---|---|---|
| 0 | [~] `avaliar.py` e linha de base | Escolha do trio e do voto (seções 1a e 6): linha de base com o Grounding DINO, OWLv2, YOLOE, híbrida com SigLIP; `avaliar.py --voto` | pytest de `avaliar.py`; tabelas do `avaliar.py` |
| 1 | [ ] | Entrada por lote com sorteio treino/teste em `imagens.csv`; `anotar.py` roda os anotadores e grava `propostas/<anotador>/`; `votar.py` aplica o 3oo3, grava `labels/` das aprovadas e gera `treino.txt`, `teste.txt` e `data.yaml`; `visualizar.py` lê as propostas | pytest do voto com caixas sintéticas |
| 2 | [ ] | `revisar.py`: servidor e API só de leitura; a página atual servida por ele | pytest com o servidor numa thread |
| 3 | [ ] | Edição básica: trocar classe, remover, aceitar, salvar e próxima, descartar | pytest da API; teste manual |
| 4 | [ ] | Desenhar, mover e redimensionar caixas; desfazer | teste manual (Chrome headless para captura) |
| 5 | [ ] | Registro RF13, auditoria das aprovadas e `metricas.py` | pytest com registros sintéticos |
| 6 | [ ] | Novas classes (RF14); modo segmentado sem classe (padrão no teste) e modo sem pré-anotação | pytest; teste manual |

## Decisões

| # | Questão | Recomendação ou decisão |
|---|---|---|
| 1 | ~~Ferramenta própria ou Label Studio?~~ | **Decidido (2026-10-28)**: ferramenta própria, a mais simples possível. |
| 2 | Onde ficam as classes? Hoje há `anotacao/classes.yaml` (anotador) e o `data.yaml` de cada saída; uma classe nova pela página (RF14) precisa ir aos dois. | `classes.yaml` como fonte, `data.yaml` gerado a partir dele. |
| 3 | ~~Um ou vários revisores?~~ | **Decidido (2026-10-28)**: um revisor, local. Sem trava por imagem nem identificação por enquanto. |
| 4 | ~~Um anotador ou vários?~~ | **Decidido (2026-10-28)**: três anotadores com voto 3oo3; quem não passa vai à revisão humana (seção 1a). |
| 5 | ~~O teste chega ao revisor com as propostas dos anotadores ou sem elas?~~ | **Decidido (2026-10-28)**: segmentado e sem classe. Os objetos chegam delimitados para poupar a seleção; a classe é do revisor (seção 5). |
| 6 | ~~O voto exige a mesma classe ou só o mesmo material?~~ | **Decidido (2026-10-28)**: mesma classe. Por material aprovaria mais, mas a imagem ficaria sem classe definida para o treino. |
| 7 | ~~Proporção treino/teste e unidade do sorteio~~ | **Decidido (2026-10-28)**: sorteio por lote de captura, 1 lote em cada 5 para o teste. Frames seguidos da esteira são quase iguais; sortear imagem a imagem vazaria cenas entre os conjuntos. |

## Notas da sessão que gerou o plano

- Qualidade observada do Grounding DINO (`tiny` e `base`) em fotos de `legado/database/tcc-0CF`: caixas bem localizadas, classes frequentemente erradas (PET transparente como `Glass bottle`; copos e potes de vidro, fora da lista, como tampa ou garrafa plástica). Reforça que trocar classe precisa ser a ação mais rápida.
- Testado em CPU (~10 s por foto de 12 MP no `tiny`) e, depois, na GTX 1650 (CUDA), onde o `avaliar.py` roda as 88 fotos de validação.
- Ambiente de teste usado: venv isolado com torch 2.14.1, transformers 5.21.0 (Python 3.14).
