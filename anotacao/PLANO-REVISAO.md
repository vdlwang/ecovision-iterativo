# Plano — framework de anotação e página de revisão

Escopo atual do projeto (tarefa T1 do [`OBJETIVO.md`](../OBJETIVO.md), que descreve o sistema completo: fluxo, voto 3oo3, bases de treino e teste). Requisitos da monografia (`docs/ecovision-iterativo-prelim.pdf`): RF11 (pré-anotação), RF12 (revisar), RF13 (registro de tempo e correções), RNF08 (usabilidade).

**Objetivo**: um framework genérico em que qualquer anotador (detector de vocabulário aberto, classificador, o próprio YOLO) grava propostas num formato comum, e uma página local para ver essas propostas, corrigi-las e editá-las até virarem anotações finais no formato YOLO. Voto entre anotadores, sorteio treino/teste, auditoria e métricas ficam para as tarefas seguintes do `OBJETIVO.md`, mas o formato já deixa espaço para eles.

**Status**: `[ ]` pendente · `[x]` feito (com hash) · `[~]` parcial

**Ponto de partida**:
- `anotar.py` (`e502a35`): o Grounding DINO propõe caixas e as grava direto em `labels/`, no formato YOLO. Desde a fase 1 (`8a0253d`), grava propostas em `propostas/<anotador>/` e o status em `imagens.csv`.
- `visualizar.py` (`3084516`): página estática (`file://`, só leitura) com as caixas de `labels/`; desde a fase 1, também as propostas.
- `avaliar.py` (`b70ac8a`): mede um anotador contra os rótulos da equipe em `legado/database`.

A ideia é separar o que o anotador propõe do que o revisor aprova, e evoluir a página para uma de revisão, servida por um servidor Python local.

---

## 1. Propostas separadas das anotações finais

Gravar as propostas em `labels/` mistura duas coisas: o Ultralytics trata imagem sem objetos como fundo (uma imagem não revisada entraria no treino como negativo falso), e a proposta original se perde, o que impede medir o anotador (RF13).

```
anotacoes/
├── images/
├── propostas/<anotador>/<nome>.json  # saída de cada anotador (imutável)
├── labels/<nome>.txt                 # caixas finais, formato YOLO, só depois da revisão
├── revisoes/<nome>.json              # registro da revisão (seção 5)
├── imagens.csv                       # nome, status (pendente, revisada, descartada)
├── revisadas.txt                     # gerado de imagens.csv; o data.yaml aponta para ele
└── data.yaml
```

- **Proposta**: `{"anotador", "versao", "classes": <hash do classes.yaml>, "caixas": [{"classe", "confianca", "caixa": [x1, y1, x2, y2]}]}`, com a caixa em pixels da imagem gravada. Guardar a confiança é o que permite ordenar a fila pela incerteza (RF10), o que os `.txt` de hoje não fazem.
- **`imagens.csv`** é a fonte do estado. O sistema completo acrescenta colunas (lote, conjunto, voto; `OBJETIVO.md`, seção 2) sem mudar as do framework.
- **Compatibilidade**: `anotar.py --aceitar` copia as propostas de um anotador para `labels/` e marca a imagem como `revisada`, para quem quiser o comportamento de hoje (proposta direto como rótulo).

## 2. Anotadores intercambiáveis

`anotar.py --anotador NOME` escolhe o anotador; cada um é uma classe com `anotar(imagem) -> [(classe, confianca, caixa)]` e um nome, registrada num dicionário. O Grounding DINO atual (classe `Anotador`) é o primeiro. Todos recebem as classes do `classes.yaml`; o que cada um faz com o `prompt` é dele. Um anotador que só reclassifica (SigLIP) recebe também as caixas de outro.

Vários anotadores podem rodar sobre a mesma saída, um por vez (na GTX 1650 não cabem juntos), e cada um grava em `propostas/<anotador>/`. O `avaliar.py` passa a aceitar `--anotador` e, depois, a ler propostas já gravadas em vez de rodar o modelo de novo. Quais anotadores entram, e como votam, é a tarefa T2 do `OBJETIVO.md`.

## 3. Arquitetura

- **Servidor**: `anotacao/revisar.py` com `http.server` da biblioteca padrão (`ThreadingHTTPServer`), só em `localhost`, sem dependência nova. Poucos endpoints e um revisor por vez não justificam um framework; se crescer (vários revisores, login), migrar para FastAPI.
- **Página**: HTML + JavaScript sem build, evoluindo do `visualizar.html`. Fica fora do `frontend/` da operação: papéis diferentes (revisor e operador) e pode rodar noutro computador (RNF05).
- **Gravações atômicas**: arquivo temporário e depois `os.replace`, para um Ctrl+C no meio não corromper um `.txt`.

| Método | Rota | Função |
|---|---|---|
| GET | `/api/imagens` | Lista com status, menor confiança e anotadores que propuseram |
| GET | `/api/imagens/<nome>` | Propostas de cada anotador e revisão atual, se houver |
| PUT | `/api/imagens/<nome>` | Grava as caixas finais em `labels/`, o registro e o status |
| GET | `/api/classes` | Classes do `classes.yaml` |
| GET | `/images/<arquivo>` | A imagem |

## 4. Interações da página

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

Caixa proposta aparece tracejada e com a confiança; depois de tocada pelo revisor, fica contínua. A fila mostra só as `pendente` por padrão, com filtro por status e ordem por confiança, para começar pelas incertas (RF10). Com mais de um anotador, a página mostra as propostas de um por vez (seletor) ou todas, coloridas por anotador; a vista de concordância do voto é a tarefa T7 do `OBJETIVO.md`. Uma imagem `revisada` pode ser reaberta e editada de novo.

## 5. Registro da revisão (RF13)

`revisoes/<nome>.json` guarda:

- **Tempo ativo**: o cronômetro pausa quando a aba perde o foco ou depois de 60 s sem interação.
- **Desfecho de cada caixa**: `aceita`, `classe_corrigida` ou `adicionada`; as propostas que sumiram vão em `removidas`. `caixa_ajustada` fica para a fase 4 (ver abaixo).
- **Versões** do anotador de base e das classes que geraram as propostas.
- **Revisor**: campo já previsto, mesmo com um revisor só (ver decisão 3).
- **Só a última revisão** (decidido em 2026-11-09): o arquivo é sobrescrito a cada revisão.

O servidor calcula os desfechos comparando cada caixa com a proposta de origem, que a página indica pelo índice. Enquanto as caixas não se movem, ele recusa uma caixa que diz vir de uma proposta mas tem outras coordenadas, para que o registro nunca chame de `aceita` uma caixa alterada.

**Para depois** (anotado em 2026-11-09, não implementado):
- **Limiar de `caixa_ajustada`** (fase 4): IoU com a proposta abaixo de um limiar (proposta inicial: 0,9). Uma caixa pode ter dois desfechos (`classe_corrigida` e `caixa_ajustada`), então o campo vira lista.
- **Histórico de sessões**: hoje a revisão de uma imagem reaberta (fase 5) sobrescreve a anterior. Para medir o anotador, vale a primeira; se as métricas (T10) precisarem, o registro vira uma lista de sessões.

O registro é gravado desde a primeira versão da edição, mesmo sem `metricas.py` (tarefa T10 do `OBJETIVO.md`): sem ele, o tempo das primeiras revisões se perde.

## Fases

A fase 1 muda o formato sem mudar o que o usuário vê; as fases 2 e 3 já entregam uma ferramenta usável (trocar classe e remover caixa, os erros mais comuns hoje); 4 e 5 completam a edição.

| # | Status | Entrega | Verificação |
|---|---|---|---|
| 1 | [x] `8a0253d` | Formato da seção 1 e anotadores da seção 2: `anotar.py --anotador` grava `propostas/<anotador>/` e `imagens.csv`; `--aceitar`; `visualizar.py` mostra propostas (com a confiança) e anotações finais | pytest com propostas sintéticas; o Grounding DINO grava o mesmo que hoje |
| 2 | [x] `ad4170c` | `revisar.py`: servidor e API só de leitura; a página atual servida por ele, com a fila | pytest com o servidor numa thread |
| 3 | [x] `7b123b9` | Edição básica: trocar classe, remover, aceitar, salvar e próxima, descartar (apaga o `.txt`); registro da revisão. `revisadas.txt` e `data.yaml` já vêm da fase 1. Só pendentes são editáveis | pytest da API; teste manual |
| 4 | [ ] | Desenhar, mover e redimensionar caixas; desfazer | teste manual (Chrome headless para captura) |
| 5 | [ ] | Reabrir revisadas; seletor de anotador; atalhos completos da seção 4 | teste manual |

## Decisões

| # | Questão | Recomendação ou decisão |
|---|---|---|
| 1 | ~~Ferramenta própria ou Label Studio?~~ | **Decidido (2026-10-28)**: ferramenta própria, a mais simples possível. |
| 2 | ~~Onde ficam as classes?~~ | **Decidido (2026-11-10)**: `classes.yaml` é a fonte. A lista `nomes` (60 classes TACO e `Background`, na ordem do `best.pt` e de `legado/database`) dá os ids e gera o `data.yaml`; `classes` é o subconjunto que o anotador procura, com prompt e material. Uma classe nova pela página (RF14) entra no fim de `nomes`. |
| 3 | ~~Um ou vários revisores?~~ | **Decidido (2026-10-28)**: um revisor, local. Sem trava por imagem nem identificação por enquanto. |
| 9 | ~~Uma página ou duas?~~ | **Decidido (2026-11-09)**: duas. `visualizar.py` continua gerando a página estática (`file://`, serve no Colab); `revisar.html` é servida pelo `revisar.py` e vira o editor. Aceita-se algum HTML repetido. |
| 10 | ~~Acesso de outro computador (RNF05)?~~ | **Decidido (2026-11-09)**: por enquanto só `127.0.0.1`; uma opção `--host` quando for preciso. |

As decisões 4 a 7 (voto, teste sem classe, mesma classe no voto, sorteio por lote) e a 8 (vidro) são do sistema completo e estão no `OBJETIVO.md`.

## Notas

- Qualidade observada do Grounding DINO (`tiny` e `base`) em fotos de `legado/database/tcc-0CF`: caixas bem localizadas, classes frequentemente erradas (PET transparente como `Glass bottle`; copos e potes de vidro, fora da lista, como tampa ou garrafa plástica). Reforça que trocar classe precisa ser a ação mais rápida.
- Testado em CPU (~10 s por foto de 12 MP no `tiny`) e, depois, na GTX 1650 (CUDA), onde o `avaliar.py` roda as 88 fotos de validação.
- Ambiente de teste usado: venv isolado com torch 2.14.1, transformers 5.21.0 (Python 3.14).
