# Plano — plataforma web de revisão das anotações

Branch de origem: `feature/anotacao-assistida` (`3084516`). Requisitos da monografia (`docs/ecovision-iterativo-prelim.pdf`): RF12 (revisar), RF13 (tempo e correções), RF14 (novas classes), RNF08 (usabilidade), seção 5.3.4 (viés de automação).

**Status**: `[ ]` pendente · `[x]` feito (com hash) · `[~]` parcial

**Ponto de partida**: o `anotar.py` grava as propostas do Grounding DINO direto em `labels/`, e o `visualizar.py` gera uma página estática (`file://`, só leitura) com as caixas. A ideia é evoluir essa página para uma de revisão, servida por um servidor Python local que lê as propostas e grava as anotações corrigidas.

---

## 1. Separar proposta de anotação revisada (decisão prévia)

Problemas de gravar as propostas em `labels/`:

- O Ultralytics trata imagem sem objetos como fundo: uma imagem não revisada, ou com objetos que o modelo não achou, entraria no treino como negativo falso.
- Sem guardar a proposta original, não dá para medir a precisão do anotador automático (RF13).

Estrutura proposta:

```
anotacoes/
├── images/
├── propostas/<nome>.json   # saída do anotar.py: classe, confiança, caixa (imutável)
├── labels/<nome>.txt       # só para imagens revisadas, formato YOLO
├── revisoes/<nome>.json    # registro da revisão: tempos e ação sobre cada caixa
├── revisadas.txt           # lista de imagens revisadas; data.yaml aponta train para ela
└── data.yaml
```

Só entram no treino as imagens de `revisadas.txt`. A confiança passa a ser guardada, e a página pode mostrá-la e ordenar pelas mais incertas.

## 2. Arquitetura

- **Servidor**: `anotacao/revisar.py` com `http.server` da biblioteca padrão (`ThreadingHTTPServer`), só em `localhost`, sem dependência nova. Poucos endpoints e um revisor por vez não justificam um framework; se crescer (vários revisores, login), migrar para FastAPI.
- **Página**: HTML + JavaScript sem build, evoluindo do `visualizar.html`. Fica fora do `frontend/` da operação: papéis diferentes (revisor e operador) e pode rodar noutro computador (RNF05).
- **Gravações atômicas**: arquivo temporário e depois `os.replace`, para um Ctrl+C no meio não corromper um `.txt`.

| Método | Rota | Função |
|---|---|---|
| GET | `/api/imagens` | Lista com status (pendente, revisada, descartada) e menor confiança |
| GET | `/api/imagens/<nome>` | Propostas e revisão atual, se houver |
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

Caixa proposta aparece tracejada e com a confiança; depois de tocada pelo revisor, fica contínua. Lista filtrável por status e ordenável por confiança, para começar pelas incertas (RF10).

## 4. Registro da revisão (RF13)

`revisoes/<nome>.json` guarda:

- **Tempo ativo**: o cronômetro pausa quando a aba perde o foco ou depois de 60 s sem interação.
- **Desfecho de cada caixa**: `aceita`, `classe_corrigida`, `caixa_ajustada` (IoU com a proposta abaixo de um limiar), `removida` ou `adicionada`.
- **Versões** do modelo e das classes que geraram a proposta.
- **Revisor**: campo já previsto, mesmo com um revisor só (ver decisão 3).

`anotacao/metricas.py` lê os registros e calcula: precisão e recall do anotador automático (casamento por IoU ≥ 0,5, com a revisão como referência), tempo médio por imagem e por objeto, taxa de cada tipo de correção.

## 5. Viés de automação (seção 5.3.4)

Marcação "sem pré-anotação" por imagem: o servidor esconde as propostas e o revisor anota do zero. Comparar com as revisadas mede o viés e dá o tempo de anotação manual, que é a linha de base do ganho.

## 6. Escolha do anotador (antes da fase 1)

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

**Como escolher**: `anotacao/avaliar.py` (~1 dia) calcula o mAP@0,5, por classe e por material, de cada candidato nas fotos de `legado/database/*/YOLO_dataset/validation`, que têm rótulos da equipe nas mesmas 6 classes do `classes.yaml` (polígonos de 4 pontos → caixas). Ressalvas: fotos paradas, sem esteira; o vazamento entre os cenários não pesa, porque nenhum candidato treinou nelas. O script serve à monografia (objetivo 3) e é reaproveitado a cada ciclo.

**Ordem**: (1) `avaliar.py` com o Grounding DINO como linha de base; (2) OWLv2 e YOLOE; (3) híbrida com SigLIP; (4) SAM 2/3 só se as caixas virarem o problema.

Fontes: [SAM 3 — Ultralytics](https://docs.ultralytics.com/models/sam-3), [Ultralytics 8.3.237](https://newreleases.io/project/pypi/ultralytics/release/8.3.237), [SAM 3 — Transformers](https://huggingface.co/docs/transformers/model_doc/sam3), [Grounding DINO vs YOLOE — Roboflow](https://playground.roboflow.com/models/compare/grounding-dino-vs-yoloe), [Open-vocabulary detection — Fora Soft](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/open-vocabulary-detection-grounding-dino-florence-2-rtdetr-rfdetr). Levantamento de 2026-10-27; custos e cabimento na GPU são estimativas, não medidos.

---

## Fases

A fase 0 define o modelo que gera as propostas. As fases 1–3 já entregam uma ferramenta usável (corrige classe e remove caixas erradas, os erros mais comuns hoje); 4–6 completam os requisitos.

| # | Status | Entrega | Verificação |
|---|---|---|---|
| 0 | [ ] | Escolha do anotador (seção 6): `avaliar.py`, linha de base com o Grounding DINO, comparação com OWLv2, YOLOE e a híbrida com SigLIP | pytest de `avaliar.py`; tabela de mAP |
| 1 | [ ] | `anotar.py` grava `propostas/*.json`; `labels/`, `revisadas.txt` e `data.yaml` no formato novo; `visualizar.py` lê as propostas | pytest |
| 2 | [ ] | `revisar.py`: servidor e API só de leitura; a página atual servida por ele | pytest com o servidor numa thread |
| 3 | [ ] | Edição básica: trocar classe, remover, aceitar, salvar e próxima, descartar | pytest da API; teste manual |
| 4 | [ ] | Desenhar, mover e redimensionar caixas; desfazer | teste manual (Chrome headless para captura) |
| 5 | [ ] | Registro RF13 e `metricas.py` | pytest com registros sintéticos |
| 6 | [ ] | Novas classes (RF14) e modo sem pré-anotação | pytest; teste manual |

## Decisões pendentes

| # | Questão | Recomendação |
|---|---|---|
| 1 | Ferramenta própria ou Label Studio? O Label Studio já edita caixas, importa predições com confiança e registra o tempo por anotação; custa um servidor Django com banco, conversões de formato na ida e na volta, e menos controle sobre o registro por caixa e o modo sem pré-anotação. | Própria, porque a interface de revisão e a medição dela são parte do trabalho (RF12, RF13, RNF08). Se o foco for o ciclo e não a interface, o Label Studio economiza as fases 3 e 4. |
| 2 | Onde ficam as classes? Hoje há `anotacao/classes.yaml` (anotador) e o `data.yaml` de cada saída; uma classe nova pela página (RF14) precisa ir aos dois. | `classes.yaml` como fonte, `data.yaml` gerado a partir dele. |
| 3 | Um ou vários revisores? Vários ao mesmo tempo pedem trava por imagem e identificação. | Um por vez, com o campo `revisor` já gravado no registro. |

## Notas da sessão que gerou o plano

- Qualidade observada do Grounding DINO (`tiny` e `base`) em fotos de `legado/database/tcc-0CF`: caixas bem localizadas, classes frequentemente erradas (PET transparente como `Glass bottle`; copos e potes de vidro, fora da lista, como tampa ou garrafa plástica). Reforça que trocar classe precisa ser a ação mais rápida.
- Testado só em CPU (~10 s por foto de 12 MP no `tiny`); GPU disponível: GTX 1650, não testada.
- Ambiente de teste usado: venv isolado com torch 2.14.1, transformers 5.21.0 (Python 3.14).
