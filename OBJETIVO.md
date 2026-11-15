# Objetivo — ciclo de melhoria do detector da esteira

O sistema completo que este repositório persegue: as imagens da própria esteira viram base de treino e de teste do YOLO, com anotação automática por voto entre modelos e revisão humana só onde ela é necessária. Requisitos na monografia preliminar (`docs/ecovision-iterativo-prelim.pdf`): RF11 a RF14, RNF08, seções 5.3.2 (taxonomia), 5.3.4 (viés de automação) e 5.3.5 (divisão dos dados). Fluxo desenhado em `docs/diagrams/diagrama_v3.drawio`.

**Escopo atual**: o **framework de anotação** (anotadores intercambiáveis que gravam propostas) e a **página de visualização, correção e edição** dos resultados, planejados em [`anotacao/PLANO-REVISAO.md`](anotacao/PLANO-REVISAO.md) (tarefa T1); em seguida, a **pipeline com múltiplos anotadores** (seção 6; ordem: T5, interface de detector e `avaliar.py` sobre propostas, OWLv2 e YOLOE, T3, T6, T14). Os demais passos do fluxo estão nas [tarefas](#tarefas), com o que já foi decidido sobre eles.

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

O framework (T1) grava as propostas de cada anotador separadas das anotações finais, e o status de cada imagem, num banco SQLite (`anotacoes.sqlite`, desde 2026-11-13; antes, `imagens.csv`), que é a fonte do estado. A tabela `imagens` já tem as colunas do sistema completo:

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

Com o voto, a pergunta deixa de ser qual é o melhor anotador e passa a ser **que trio, quando concorda, quase nunca erra, e concorda com frequência suficiente** para poupar revisão. Um anotador preciso mas muito parecido com outro vale menos que um mais fraco de outra família. Trio adotado (decisão 17, 2026-11-13): Grounding DINO, OWLv2 e o YOLO da equipe (`best.pt`); o YOLOE e a híbrida com SigLIP ficam como alternativas para o lugar de um deles. Na GTX 1650 os três não cabem juntos: o `anotar.py` roda um anotador por vez sobre o lote inteiro.

Nas fotos testadas, o Grounding DINO localiza bem e erra a classe; por isso entram também opções que só **reclassificam** as caixas. Custo = esforço para encaixar no `anotar.py` (a classe `Anotador` já isola o modelo).

| Opção | Como entra | Licença | GTX 1650 (4 GB) | Custo | Observações |
|---|---|---|---|---|---|
| Grounding DINO tiny/base (atual) | — | Apache 2.0 | Cabe | — | Referência de precisão para rótulos offline |
| OWLv2 (**feito**, 2026-11-12) | `transformers`, mesma API; pontuação por texto de classe (dispensa o mapeamento por token) | Apache 2.0 | Cabe (base) | ~½ dia | Concorrente mais direto. Medido abaixo: classe bem melhor que a do Grounding DINO |
| YOLO-World / YOLOE | `ultralytics` (`set_classes`) | GPL-3.0 / AGPL-3.0 | Tempo real | ~½ dia | Mais rápidos, menos precisos; o YOLOE treina como YOLO comum e poderia virar o detector da esteira |
| Grounding DINO + SAM 2 | Caixas do DINO como prompt do SAM | Apache 2.0 | Cabe (SAM 2 pequeno) | ~1 dia | Melhora caixas, não a classe |
| SAM 3 (texto → máscaras e caixas) | `ultralytics` ≥ 8.3.237 (`SAM3SemanticPredictor`) ou `transformers` | Licença própria da Meta (verificar) | **Não cabe**: 848M parâmetros, checkpoint de ~3,4 GB, o guia oficial pede ≥ 16 GB; roda no Colab | ~1–2 dias | Pesos baixados à mão. Papel previsto: só gerar caixas e candidatas (abaixo) |
| Florence-2 | `transformers` com `trust_remote_code` | MIT | Cabe | ~1 dia | Sem confiança por caixa: quebra a ordenação por incerteza (RF10) |
| VLM local (Qwen2.5-VL/Qwen3-VL 3B–7B) | Caixas em JSON na resposta | Apache 2.0 (maioria) | 3B quantizado cabe; 7B não | ~2–3 dias | Lento, sem confiança calibrada; bom para decidir material |
| APIs (Gemini, DINO-X / Grounding DINO 1.6 Pro) | HTTP | Comercial, por imagem | — | ½–1 dia | Imagens saem da máquina (RNF09/LGPD) |
| Detector próprio (`best.pt` e retreinos) (**feito**, 2026-11-13: `--anotador yolo`) | `ultralytics` | AGPL-3.0 | Cabe | Baixo | Aprendizado ativo clássico; herda os próprios erros; terceiro anotador do trio. Medido abaixo: classe precisa, cobertura baixa |

**Híbrida (hipótese a testar)**: manter as caixas do Grounding DINO e reclassificar cada recorte com SigLIP ou CLIP (`transformers`, Apache 2.0, ~½–1 dia), que compara o recorte com textos como "clear plastic bottle" e "glass bottle". Um VLM pode ser chamado só nos recortes ambíguos.

**Como escolher**: `anotacao/avaliar.py` mede cada candidato (acerto de classe e de material com as caixas verdadeiras; precisão e recall por limiar de confiança) nas fotos de `legado/database/*/YOLO_dataset/validation`, que têm rótulos da equipe nas mesmas 6 classes do `classes.yaml` (polígonos de 4 pontos → caixas). Ressalvas: fotos paradas, sem esteira; o vazamento entre os cenários não pesa para os detectores de vocabulário aberto, que não treinaram nelas; o `best.pt` treinou em fotos da equipe que não estão no repositório (ressalva na seção do YOLO, abaixo). O script serve à monografia (objetivo 3) e é reaproveitado a cada ciclo.

**Ordem**: (1) `avaliar.py` com o Grounding DINO como linha de base; (2) OWLv2 e YOLOE; (3) híbrida com SigLIP; (4) `avaliar.py --voto` com o trio; (5) SAM 2/3 só se as caixas virarem o problema.

**SAM 3 como gerador de caixas e candidatas (alternativa, 2026-11-12).** Não como anotador do trio nem para dar a classe: só para produzir as caixas, inclusive as candidatas do clique, que os outros anotadores classificam ou o revisor completa. A motivação é desacoplar a localização da classe: hoje uma só confiança decide se a caixa aparece (`confianca`), se vira candidata (`piso`) e se a classe é mostrada (`confianca_classe`), e os três limiares foram escolhidos sobre a pontuação do Grounding DINO, que mistura "é um objeto" com "é desta classe". Com caixas de um segmentador, a decisão de mostrar ou não uma caixa passaria a depender da qualidade da máscara, e a da classe, só do classificador, o que permite rever as questões de limiar (decisões 15 e 16) separadamente. Não roda na GTX 1650; seria rodado no Colab e gravado como proposta de um anotador, como os outros. Entra só se a cobertura sem classe ou o clique virarem o gargalo depois do trio e do SigLIP.

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
1. ~~Decidir a taxonomia do vidro~~: feito (decisão 8). `Glass jar` ("glass jar") e `Glass cup` ("drinking glass") no fim do `classes.yaml`.
2. Permitir mais de um prompt por classe, com a pontuação máxima entre eles: um prompt não cobre copo, pote e tigela.
3. ~~Registrar as correções dos rótulos da equipe~~: feito, em `anotacao/correcoes_rotulos.yaml`, que o `avaliar.py` aplica na leitura (`--sem-correcoes` desliga).
4. ~~Refazer a linha de base~~: feito (abaixo). O SigLIP herda o mesmo cuidado: as descrições têm de corresponder aos objetos das fotos, não ao nome TACO.

### Linha de base com o vidro em três classes (2026-11-09)

**Correções dos rótulos.** As 97 caixas `Glass bottle` da equipe, classificadas olhando os recortes e as mesmas cenas nos quatro cenários: 54 `Glass jar`, 40 `Glass cup` (24 copos, 16 taças, 8 tigelas) e 3 `Drink can`. Nenhuma garrafa de vidro. O caso duvidoso é o copo de requeijão (11 caixas, um objeto em várias cenas): embalagem com aba para tampa, usada como copo. Ficou como `Glass jar`, com nota no arquivo.

**Resultado** (Grounding DINO tiny, 88 fotos, 375 caixas, 8 classes):

| | 2026-10-27 (6 classes, sem correções) | 2026-11-09 |
|---|---|---|
| Classe certa | 46% | 51% |
| Material certo | 50% | 58% |
| Precisão / recall em 0,35 | 0,39 / 0,33 | 0,48 / 0,42 |

- `Glass jar` acerta 47%, `Glass cup` 45%. Entre si, trocam pouco (6 e 4 caixas). Perdem mais para plástico e lata.
- **`Glass bottle` virou o ralo do PET**: sem nenhuma caixa verdadeira, recebe 35 previsões, 28 delas de `Clear plastic bottle` (que acerta só 26%). Na esteira haverá garrafas de vidro, então a classe fica. Mas o prompt "glass bottle" atrai garrafas transparentes de qualquer material. É o primeiro caso para o SigLIP, ou para vários prompts por classe.
- Os números não são comparáveis um a um com os de 2026-10-27: as classes e a verdade mudaram juntas.

### Mais classes no anotador (2026-11-10)

Os rótulos passaram a usar as 60 classes TACO e `Background` (`nomes` no `classes.yaml`, decisão 2 do plano do T1); o anotador continua procurando só as 8 de `classes`. Medido com o `avaliar.py`, mesmas 88 fotos e 375 caixas:

| Classes no anotador | Classe certa | Material | P / R em 0,35 | Caixas na genérica |
|---|---|---|---|---|
| 8 (linha de base) | 51% | 58% | 0,48 / 0,42 | — |
| 60 TACO (nome TACO como prompt nas 52 novas) | 10% | 38% | 0,12 / 0,11 | — |
| 8 + `Unlabeled litter` concorrendo ("trash object" / "object" / "piece of trash") | 41% / 35% / 36% | 48% / 41% / 42% | 0,44–0,47 / 0,39–0,41 | 60 / 114 / 119 |
| 8 + `Unlabeled litter` de reserva (mesmos prompts) | 46% / 47% / 45% | 54% / 55% / 54% | 0,45–0,47 / 0,39–0,41 | 18 / 4 / 12 |

- **60 classes**: as novas absorvem os objetos (lata vira `Disposable food container`, pote vira `Disposable plastic cup`, tampa vira `Aerosol`). Confirma o teste qualitativo de 2026-10-27.
- **Classe genérica**: serviria para dar caixa aos objetos da esteira fora das 8. Concorrendo, rouba previsões. Como reserva (`reserva: true` no `classes.yaml`: só vence se nenhuma comum chega ao limiar) quase não rouba, mas a frase a mais no prompt muda a pontuação das outras e custa 4 a 6 pontos de classe. O ganho não aparece aqui: todo objeto destas fotos está entre as 8.
- **Pendente**: decidir entre a genérica numa passada separada (as 8 ficam como na linha de base; o dobro do tempo de GPU), a genérica no mesmo prompt (−4 pontos) ou nenhuma até haver fotos da esteira. O campo `reserva` já existe; nenhuma classe o usa.

### Ajustes futuros da avaliação (2026-11-10)

- **Cobertura sem classe no limiar.** O "não localizadas" do `avaliar.py` olha as consultas brutas do modelo, antes do limiar, e deu 100%; o recall da detecção exige a classe certa. Nenhum dos dois diz se todo objeto recebe caixa na proposta. Falta, por limiar: a fração dos objetos verdadeiros com alguma caixa (IoU ≥ 0,5, qualquer classe) e a fração das imagens completas (nenhum objeto sem caixa), a que importa para o treino (seção 2). Medida avulsa feita (abaixo); falta levá-la ao `avaliar.py`.
- ~~**Limiar da anotação pela cobertura**~~: feito (abaixo), padrão do `anotar.py` em 0,20. Em `legado/images/20250323_184428.jpg` saiu nenhuma caixa: as latas e tampas pontuam 0,33–0,35, logo abaixo do limiar de 0,35 (com 0,30 saem 4 caixas, com 0,20 saem 10). Até a fase 4 do T1, imagem com objeto sem caixa é descartada, não salva.
- **`taco_to_material` do backend** não tem `Carded blister pack` (cai em `other`).

### Cobertura sem classe e limiar da anotação (2026-11-11)

Grounding DINO `tiny`, mesmas 88 fotos e 375 caixas (8 classes, rótulos corrigidos), com os filtros e o NMS do `anotar.py`. Script avulso, ainda fora do `avaliar.py`. Uma caixa verdadeira está **coberta** se alguma proposta tem IoU ≥ 0,5 com ela, qualquer que seja a classe; a imagem está **completa** se todas as suas caixas estão cobertas.

**Posição.** Entre as 900 consultas brutas, a melhor caixa de cada objeto tem IoU ≥ 0,75 em 98% dos casos e ≥ 0,9 em 68% (mediana 0,93). Quando o modelo acha o objeto, a caixa é boa. O que tira o objeto da proposta é a confiança: a maior entre as consultas com IoU ≥ 0,5 tem mediana 0,39, e um quarto dos objetos fica abaixo de 0,34 (p10 0,24; p5 0,16).

| Limiar | Cobertos | Cobertos com IoU ≥ 0,75 | Imagens completas | Caixas por imagem | Sobra por imagem |
|---|---|---|---|---|---|
| 0,05 | 99% | 94% | 98% | 58,3 | 54,1 |
| 0,10 | 98% | 93% | 93% | 19,4 | 15,2 |
| 0,15 | 95% | 90% | 84% | 11,2 | 7,1 |
| **0,20** | **92%** | **87%** | **73%** | **7,8** | **3,9** |
| 0,25 | 89% | 84% | 66% | 5,8 | 2,0 |
| 0,30 | 82% | 78% | 56% | 4,6 | 1,1 |
| 0,35 (antigo padrão) | 72% | 69% | 41% | 3,7 | 0,6 |

As fotos têm em média 4,3 objetos. "Sobra" são as propostas que não cobrem nenhum objeto rotulado, e remover cada uma custa uma tecla. Em todo limiar, as caixas que cobrem um objeto têm IoU mediano de 0,92, e a classe delas acerta ~57%: baixar o limiar não piora a classe das caixas que acham objeto.

- **Decisão**: padrão do `anotar.py` em 0,20 (era 0,35). Com 0,35, 59% das imagens ficavam com objeto sem caixa, que até a fase 4 só podiam ser descartadas. Com 0,20, 73% chegam completas, ao custo de ~4 caixas a remover por imagem. 0,15 (84% completas, ~7 a remover) fica como alternativa se a fase 4 trouxer remoção em lote.
- **Para a fase 4 do T1**: desenhar do zero fica raro (5–8% dos objetos em 0,15–0,20); remover vira a ação mais comum (vale um atalho para remover as caixas de confiança baixa, ou mostrá-las com outro estilo); ajustar continua necessário (~um terço dos objetos abaixo de IoU 0,9).
- **Ressalvas**: parte da sobra pode ser objeto real de classe que a equipe não rotulou, ou pedaço de objeto (não separado); fotos de celular, com as mesmas cenas nas quatro validações; os rótulos da equipe são polígonos de 4 pontos convertidos em caixa. Refazer com quadros da esteira (T4).
- **Não muda**: as medidas anteriores de precisão e recall continuam em 0,35, o limiar em que foram medidas. O `avaliar.py` usa o `CONFIANCA_PADRAO` só para decidir a classe de reserva, que nenhuma classe usa hoje.

### Caixas contidas e propostas sem classe (2026-11-11)

Na revisão apareceram caixas dentro de outras: o topo de uma lata proposto como `Plastic bottle cap` dentro da caixa `Drink can`, uma `Glass cup` fraca em volta da lata, duas caixas de papel uma dentro da outra. O NMS não as pega: o IoU entre uma caixa pequena e a grande que a contém é baixo. Medido com a **contenção** (fração da área da caixa menor dentro da maior), sobre as mesmas saídas brutas da seção anterior. Nos rótulos da equipe, só 1 das 375 caixas está dentro de outra (≥ 80%).

| Limiar 0,20, depois do NMS | Cobertos | Imagens completas | Caixas por imagem | Sobra por imagem |
|---|---|---|---|---|
| Só NMS | 92% | 73% | 7,8 | 3,9 |
| Remove a grande que envolve uma menor mais confiante | 84% | 47% | 6,6 | 3,1 |
| **Remove a contida numa maior mais confiante** | **91–92%** | **73%** | **5,7–5,8** | **1,8** |
| Remove a contida, qualquer que seja a confiança | 86% | 58% | 4,7 | 1,0 |

- **A grande fica.** O Grounding DINO dá, com frequência, mais confiança a uma parte do objeto que ao objeto inteiro (o topo da lata, 0,38, dentro da lata, 0,37); remover a grande apaga o objeto.
- **A pequena sai só se a grande for mais confiante.** Sem essa condição, uma caixa grande espúria apaga o objeto de dentro.
- Contenção de 0,7, 0,8 ou 0,9 dá o mesmo resultado (± 1 ponto); em 0,15 a sobra cai de 7,1 para 3,1 por imagem, sem perder cobertura.
- **Decisão**: `--contencao 0.9` no `anotar.py`, aplicada no `filtrar` (o `avaliar.py` também a aplica). Caixas fora da esteira (papel no fundo branco) pedem outro filtro, por região de interesse, quando houver quadros da esteira (T4).

**Propostas sem classe.** Acerto de classe por faixa de confiança, entre as caixas que cobrem um objeto (limiar 0,15, com a contenção):

| Confiança | 0,15–0,20 | 0,20–0,25 | 0,25–0,30 | 0,30–0,35 | 0,35–0,40 | 0,40–0,50 | ≥ 0,50 |
|---|---|---|---|---|---|---|---|
| Caixas que cobrem objeto | 12% | 15% | 39% | 75% | 86% | 87% | 85% |
| Classe certa, das que cobrem | 73% (11/15) | 50% (6/12) | 62% (16/26) | 53% (20/38) | 38% (32/85) | 61% (73/120) | 75% (45/60) |

- A confiança prevê se a caixa é um objeto, não se a classe está certa: a classe acerta 40–75% em toda faixa, com amostras pequenas abaixo de 0,30.
- **Decisão**: abaixo de 0,35 (`--confianca-classe`, o limiar antigo da anotação), a caixa é proposta **sem classe** e o revisor tem de dá-la ou remover a caixa. O motivo não é a classe ser pior ali, e sim o viés de automação (seção 4): as caixas entre 0,20 e 0,35 são as que o limiar antigo escondia, a maioria sem objeto, e aceitá-las com uma tecla seria fácil demais. A classe do anotador fica em `sugerida`, para medir depois (T10) se valeria mostrá-la. Desfecho novo no registro: `classe_atribuida`.

### Caixa por clique (2026-11-11)

Para os objetos que a proposta não cobre, a página de revisão oferece as caixas brutas do modelo como **candidatas**: um clique no objeto mostra a mais confiante que contém o ponto. Simulado com um clique no centro de cada caixa verdadeira, mesmas 88 fotos, candidatas com confiança ≥ 0,05 e NMS 0,8 (~50 por foto depois do filtro de área):

| Objetos | 1ª candidata com IoU ≥ 0,75 | Entre as 3 primeiras |
|---|---|---|
| Todos (375) | 90% | 97% |
| Sem caixa na proposta, limiar 0,20 (31) | 81% | 87% |
| Sem caixa na proposta, limiar 0,15 (19) | 74% | 84% |

- **Decisão**: `anotar.py --candidatas 0.05` grava as candidatas na proposta, sem classe; na página, `N` e um clique criam a caixa, `Tab` troca a candidata. A caixa nasce sem classe, como as de baixa confiança. O registro marca `"origem": "candidata"`, e o servidor recusa uma caixa que diz ser candidata e não é, o que permite medir no uso quantas vezes o clique resolve.
- **Ressalvas**: o clique simulado cai no centro exato do objeto; num objeto pequeno ou dentro de outro (a lata e o topo dela), há muitas candidatas no ponto (22 no teste da lata), mas a ordem pela confiança põe as úteis antes. Desenhar à mão continua necessário para os ~15% restantes (fase 4 do T1).

### OWLv2 (2026-11-12)

Segundo anotador do trio: `anotar.py --anotador owlv2` (`google/owlv2-base-patch16-ensemble`, uma consulta de texto por classe, com o mesmo `prompt` do `classes.yaml`), sobre a classe base `Detector`, com os mesmos filtros (piso 0,05, área máxima 0,5, NMS 0,5, contenção 0,9). Mesmas 88 fotos e 375 caixas, medidas pelo `avaliar.py` sobre as propostas gravadas; o Grounding DINO `tiny` foi anotado de novo na mesma saída e reproduz as medidas de 2026-11-11.

| | Grounding DINO 0,20 | OWLv2 0,20 | OWLv2 0,10 |
|---|---|---|---|
| Objetos cobertos | 92% | 82% | 93% |
| Imagens completas | 73% | 64% | 85% |
| Caixas / sobra por imagem | 5,8 / 1,8 | 3,8 / 0,3 | 4,7 / 0,8 |
| Classe certa (das caixas que cobrem objeto) | 57% | 75% | 76% |
| Material certo | 65% | 89% | 89% |
| Detecção com classe: precisão / recall | 0,39 / 0,52 | 0,69 / 0,62 | 0,64 / 0,71 |
| Clique: objetos sem caixa, 1ª candidata com IoU ≥ 0,75 | 25/31 (81%) | 52/68 (76%) | — |
| Candidatas por imagem | 11,3 | 2,0 | — |
| Tempo nas 88 fotos (GTX 1650, com a carga) | 2,2 min | 5,1 min | |

- **Classe muito melhor**: a confusão que restava é a do PET com o vidro (20 das 58 `Clear plastic bottle` saem `Glass bottle`) e a de potes com copos (38 dos 50 `Glass jar` saem `Glass cup`, 2% de acerto). Latas, tampas, papelão e papel acertam 96–100%. No Grounding DINO, os erros se espalham por todas as classes.
- **A pontuação tem outra escala**: o OWLv2 dá confiança mais baixa e quase sem caixa espúria (sobra de 0,3 por imagem em 0,20, contra 1,8). O limiar de leitura dele deve ser **0,10**, não 0,20: mais imagens completas que o Grounding DINO em 0,20 (85% contra 73%), com menos da metade da sobra. Como o limiar é de leitura (decisão 16), não é preciso anotar de novo: basta o voto e a página aplicarem o limiar de cada anotador (seção 6, `anotadores.yaml`).
- **`confianca_classe` de 0,35 não serve ao OWLv2**: a classe acerta 75–100% abaixo de 0,35 e só 48–58% entre 0,35 e 0,50 (onde estão os potes chamados de copo), e 89% acima de 0,50. A faixa não é monótona, então o limiar que esconde a classe tem de ser medido por anotador, e não herdado do Grounding DINO.
- **O clique fica com o Grounding DINO**: o OWLv2 grava poucas caixas abaixo do limiar (2 candidatas por foto, contra 11), porque os fragmentos vizinhos se fundem no NMS. Continua valendo a candidata de um anotador só, o de base (seção 6).
- **Frase da consulta**: `--owlv2-frase "a photo of a {}"` deu o mesmo resultado que o prompt puro (cobertura e classe a ±1–4 pontos em todo limiar; potes ainda 0%). O padrão continua o prompt puro.
- **Lento no pré-processamento**: o processador do OWLv2 sem `torchvision` usa `scipy` sobre a foto de 12 MP (~3 s por imagem). Nos quadros da webcam, bem menores, deve cair muito.
- **Para o trio**: OWLv2 e Grounding DINO concordam pouco na classe (o DINO erra muito), o que hoje faria o voto 3oo3 reprovar quase tudo por causa do DINO. Reforça a híbrida com SigLIP ou a troca do DINO; medir no T3.

### Dependência entre anotadores (2026-11-12)

O 3oo3 só funciona se os erros de classe forem pouco correlacionados: o erro que passa no voto é aquele que os três cometem juntos, na mesma classe. A localização já está boa nos anotadores medidos; a independência importa na **classe**. E quase todo detector de vocabulário aberto decide a classe com um modelo da família do CLIP:

| Anotador | O que decide a classe | Pré-treino |
|---|---|---|
| Grounding DINO | BERT + Swin, fusão texto-imagem treinada em detecção e *grounding* | O365, GoldG, Cap4M |
| OWLv2 | ViT inicializado do CLIP, autotreinado com pseudo-rótulos do OWL-ViT | WebLI (Google) |
| SigLIP (híbrida) | Contrastivo imagem-texto | WebLI (Google) |
| YOLOE | Texto pelo MobileCLIP | DataCompDR (Apple) |
| YOLO-World | Texto pelo CLIP | WIT (OpenAI) |

**Risco da híbrida**: com a classe do SigLIP, dois dos três votos de classe (OWLv2 e SigLIP) viriam de modelos contrastivos do mesmo WebLI, e o 3oo3 viraria, na classe, quase um 2oo2. Os erros do OWLv2 são de aparência (PET transparente como vidro, pote como copo), do tipo que um modelo do mesmo dado tende a repetir. O YOLOE também não escapa: a diversidade dele está na arquitetura e no treino de detecção, não na fonte da classe.

**Medida** (`avaliar.py --comparar`): sobre os objetos que os dois anotadores cobrem, quantas vezes erram juntos e quantas concordam na **mesma classe errada** (o que o voto aprovaria), contra o esperado se os erros fossem independentes **dada a classe verdadeira**: cada anotador com o mesmo acerto por classe, sorteado à parte. Assim, uma classe difícil para todos não conta como dependência; conta o erro em comum além disso.

OWLv2 × Grounding DINO, mesmas 88 fotos:

| Limiares (OWLv2 / DINO) | Objetos cobertos pelos dois | OWLv2 erra | DINO erra | Os dois erram (esperado) | Concordam | Mesma classe errada (esperado) | phi dos erros |
|---|---|---|---|---|---|---|---|
| 0,20 / 0,20 | 295 | 26% | 42% | 44 (40,1) | 55% | 23 (17,6) | 0,19 |
| 0,10 / 0,20 | 328 | 25% | 42% | 48 (42,5) | 55% | 26 (18,6) | 0,19 |
| 0,05 / 0,05 | 364 | 24% | 43% | 52 (44,6) | 54% | 27 (19,3) | 0,18 |

- **Mesmo de famílias diferentes, os erros são dependentes**: a mesma classe errada sai ~1,4 vez o esperado, e quase toda (17 de 23) é a mesma confusão, `Clear plastic bottle` → `Glass bottle`. É um erro do problema (garrafa transparente) mais que da linhagem do modelo; outros erros em comum: pote como copo (3), papelão como papel (3–4).
- **O par sozinho não basta**: 14% das concordâncias estão erradas, longe dos 95% de aprovadas corretas do critério do trio. O terceiro anotador tem de errar diferente justamente no PET × vidro.
- **Decisão**: a escolha do trio é pelo erro conjunto medido, não pela família declarada. A híbrida com SigLIP só entra num trio com o OWLv2 se `--comparar` mostrar que os dois não repetem a confusão do PET; senão, ela substitui o OWLv2, e não o DINO.
- **Alternativa para a classe, se a dependência aparecer**: DINOv2/v3 + kNN (ou regressão logística) sobre os recortes rotulados pela equipe. É um modelo só de imagem, sem texto e sem WebLI, e a classe vem de exemplos do domínio, não de linguagem: a fonte de informação mais diferente que temos. O risco é o vazamento entre as fotos (as quatro validações são as mesmas cenas); a validação tem de ser por cena, como no plano do SigLIP abaixo. Um CLIP da OpenAI no lugar do SigLIP muda o dado (WIT), mas não a família, e ganha pouco.
- **Ressalvas**: as 88 fotos são ~22 cenas em quatro cenários, então os objetos não são independentes entre si e as contagens são pequenas; o "esperado" supõe acerto por classe constante em todas as fotos. Refazer com quadros da esteira (T4).

### Vários prompts por classe (2026-11-13)

`prompt` no `classes.yaml` passou a aceitar uma lista; a classe recebe a maior pontuação entre os seus prompts (no Grounding DINO, o máximo entre os tokens de todos eles; no OWLv2, uma consulta por prompt). Duas variantes, uma iteração cada, nas mesmas 88 fotos, com o DINO lido em 0,20 e o OWLv2 em 0,10:

- **v2**, só nas confusões medidas: PET com "clear plastic water bottle" e "crushed plastic bottle"; pote com "glass food jar" e "jar with a lid"; copo com "wine glass" e "glass bowl".
- **v3**, a v2 mais um sinônimo nas outras classes: "plastic lid", "soda can", "paperboard box", "crumpled paper". `Glass bottle` fica com um prompt só, para não atrair mais.

| | DINO atual | DINO v2 | DINO v3 | OWLv2 atual | OWLv2 v2 | OWLv2 v3 |
|---|---|---|---|---|---|---|
| Objetos cobertos | 92% | 94% | 97% | 93% | 96% | 98% |
| Imagens completas | 73% | 75% | 86% | 85% | 86% | 92% |
| Sobra por imagem | 1,8 | 2,6 | 3,0 | 0,8 | 0,8 | 0,8 |
| Classe certa | 57% | 54% | 63% | 76% | 75% | 79% |
| Material certo | 65% | 64% | 72% | 89% | 87% | 91% |
| Detecção com classe: precisão / recall | 0,39 / 0,53 | 0,33 / 0,51 | 0,36 / 0,61 | 0,64 / 0,71 | 0,64 / 0,73 | 0,66 / 0,78 |

- **v3 adotada** no `classes.yaml`. O ganho se repete nos dois ângulos, como pede o plano do SigLIP: classe do DINO 56% → 61% a 0° e 58% → 65% a 45°; do OWLv2, 77% → 81% e 75% → 77%; imagens completas sobem nos quatro casos (DINO 70% → 84% e 75% → 89%; OWLv2 82% → 89% e 89% → 95%).
- **v2 piora o DINO**: sem "soda can", "crushed plastic bottle" leva as latas (acerto 59% → 28%). Prompt a mais atrai objetos de outras classes; cada um tem de ser medido junto com os demais.
- **PET**: no DINO, `Clear plastic bottle` sobe de 19% para 74%, e o PET chamado de `Glass bottle` cai de 33 para 9. O custo é que o prompt de PET agora atrai vidro e lata (16 potes, 10 copos e 10 latas como PET). No OWLv2, PET 64% → 74%.
- **Pote continua sem solução**: no OWLv2, `Glass jar` sai de 2% para 10%, e 33 de 54 ainda saem `Glass cup`. Nenhum prompt de texto separou o pote do copo. É caso para classificador por exemplos (DINOv2 + kNN), ou para rever a decisão 8 se os potes forem raros na esteira.
- **Custos**: o DINO sobe a sobra de 1,8 para 3,0 caixas por imagem; o OWLv2 cai em papelão (100% → 72%, papelão como papel, por "crumpled paper"). Com poucos objetos sem caixa visível no DINO (13 em 0,20, eram 31), a medida do clique deixa de ser comparável.
- **Dependência OWLv2 × DINO** (`--comparar`, 358 objetos): concordâncias erradas caem de 14% para 9%, mas acima do esperado (20 contra 10,8), agora espalhadas entre PET → vidro (6), pote → copo (6) e papelão → papel (4).
- **Ressalva**: os prompts foram escolhidos olhando as confusões destas fotos, e é a primeira iteração; os dois ângulos são as mesmas cenas. Conferir na esteira (T4).

### YOLO da equipe como terceiro anotador (2026-11-13)

Decisão 17: o trio é Grounding DINO, OWLv2 e o `best.pt` (YOLOv8s do TACO com fine-tuning nas fotos da equipe), `anotar.py --anotador yolo`. Ele não usa os prompts: as classes de `classes.yaml` são casadas pelo nome com as 61 do modelo, e a saída crua da rede (pontuação de cada classe em cada âncora, antes do NMS do Ultralytics) passa pela mesma base `Detector` que os outros. Conferido contra o `predict()` do Ultralytics: mesmas caixas e confianças. Roda em 26 s nas 88 fotos.

| | YOLO 0,05 | YOLO 0,20 | YOLO 0,50 |
|---|---|---|---|
| Objetos cobertos | 65% | 43% | 20% |
| Imagens completas | 19% | 9% | 8% |
| Sobra por imagem | 1,0 | 0,2 | 0,0 |
| Classe certa | 66% | 87% | 93% |
| Material certo | 74% | 91% | 95% |
| Detecção com classe: precisão / recall | 0,48 / 0,43 | 0,78 / 0,37 | 0,93 / 0,19 |

- **Preciso e cego**: quando dá caixa, a classe é a mais certa dos três; mas em 0,20 não acha 56 das 58 garrafas PET, 48 das 59 latas e 46 dos 54 potes. Acha tampas (83 de 98) e papel (38 de 43); copos, só 10 de 40. As latas que acha, chama de tampa (11).
- **Não é a resolução**: com `--yolo-lado` 960 e 1280, a cobertura em 0,20 fica em 50% e 49%.
- **Vazamento**: o `best.pt` não reproduz nestas fotos o mAP50 de 0,995 do próprio checkpoint, e prevê `Glass cup`, que os rótulos da equipe nunca usam (todo vidro é `Glass bottle`), então a classe do vidro vem do TACO. Nada indica que treinou nestas fotos, mas o `data.yaml` do treino não está no repositório; trate os números dele com cautela.
- **Erros independentes nos objetos que cobre** (v3, YOLO em 0,20): com o OWLv2, 157 objetos, os dois erram 10 (esperado 10,0), concordam em 88%, e só 3 concordâncias (2%) estão erradas; com o DINO, 152 objetos, 2 concordâncias erradas (esperado 1,1). Dos três pares, os do YOLO são os únicos sem erro em comum além da dificuldade da classe, o que é a diversidade que o voto pede: o YOLO aprendeu a classe por exemplos rotulados, não por texto.
- **Problema para o voto: a cobertura.** No 3oo3 estrito (seção 3), uma imagem só passa se os três acham os mesmos objetos; com o YOLO completo em só 9% das imagens (19% em 0,05), a aprovação fica abaixo disso, longe dos ~30% do critério. Opções para o T3: (a) a classe em 3oo3 e a localização em 2oo3, com o YOLO votando só nas caixas que propõe, e o objeto que ele não acha passando pelo voto dos outros dois; (b) ler o YOLO num limiar baixo (0,05); (c) retreinar o YOLO com a base revisada a cada ciclo (T12), o que deve subir a cobertura dele: é o aprendizado ativo previsto. Medir (a) e (b) no `avaliar.py --voto`.

### Outros pesos do YOLO e o voto medido (2026-11-13)

**Pesos** (mesmas 88 fotos, prompts v3 nos outros dois; `anotar.py --anotador yolo --nome ... --modelo ...`):

| Peso | Cobertos 0,05 / 0,20 | Completas 0,05 / 0,20 | Classe certa 0,05 / 0,20 | Material 0,05 / 0,20 |
|---|---|---|---|---|
| `best.pt` (fine-tuning, dez/2025) | 65% / 43% | 19% / 9% | 66% / 87% | 74% / 91% |
| `yolov8s.pt` (só TACO) | 54% / 44% | 23% / 15% | 81% / 86% | 85% / 88% |
| `yolov8n.pt` (só TACO) | 62% / 16% | 28% / 1% | 56% / 88% | 56% / 88% |
| `yolov8m.pt` (só TACO) | 49% / 6% | 9% / 0% | 53% / 83% | 54% / 83% |
| `150ep_best.pt` (e `97ep`, `50ep`) | 99% / 99% | 97% / 97% | 74% / 74% | 99% / 99% |

- **`taco/yolov8s.pt` é o TACO**, idêntico byte a byte a `legado/yolo_models/taco/yolov8s_100epochs-best.pt`; os READMEs diziam que era o COCO (corrigido).
- **TACO puro ≈ `best.pt`**: o `s` sem fine-tuning cobre e acerta quase o mesmo que o `best.pt`; o fine-tuning de dezembro não ajudou nestas fotos. `n` e `m` são piores (o `m` confia pouco: quase nada acima de 0,20).
- **`50ep`, `97ep` e `150ep` memorizaram estas fotos**: 99% dos objetos, 97% das imagens completas, todo objeto não vidro com a classe certa e **todo vidro como `Glass bottle`**, exatamente o rótulo original da equipe (o 74% de classe é só o vidro, que as correções mudaram). Treinaram nestas fotos ou nas mesmas cenas; a validação não serve para medi-los. O `best.pt`, que continuou o `150ep` (com um `./data.yaml` de mesmo nome, segundo o checkpoint), perdeu isso: pelo resultado, o conteúdo desse `data.yaml` era outra base.

**Voto** (`avaliar.py --voto`, DINO em 0,20 e OWLv2 em 0,10):

| Terceiro anotador | Imagens aprovadas (3oo3 estrito) | Caixas com consenso dos três | Certas | Objetos com consenso |
|---|---|---|---|---|
| nenhum (par DINO + OWLv2) | 4 (5%) | 223 | 89% | 58% |
| `best.pt` em 0,05 | 1 (1%) | 109 | 97% | 29% |
| `best.pt` em 0,20 | 1 (1%) | 94 | 99% | 25% |
| TACO `s` em 0,05 | 2 (2%) | 107 | 97% | 29% |
| TACO `s` em 0,20 | 2 (2%) | 94 | 97% | 25% |
| TACO `n` em 0,05 | 0 | 85 | 98% | 23% |
| TACO `m` em 0,05 | 0 | 71 | 99% | 19% |
| `150ep` (memorizou) | 4 (5%) | 176 | 99% | 47% |

- **(b) não resolve**: baixar o limiar do YOLO de 0,20 para 0,05 sobe o consenso por caixa de 25% para 29% dos objetos e não muda a aprovação por imagem (1–2%).
- **O gargalo é a regra por imagem, não o YOLO**: o par DINO + OWLv2 sozinho aprova 5% das fotos (12% com o DINO em 0,30, com 82% delas corretas). As fotos de validação têm ~4,3 objetos cada; basta um anotador achar uma caixa a mais ou a menos para reprovar (77 das 84 reprovações do par são por quantidade). Nos quadros da esteira, com um ou dois objetos por vez, a aprovação por imagem deve ser bem maior; medir no T4.
- **Por caixa, o YOLO faz o que se esperava**: o consenso dos três acerta 97–99%, contra 89% do par; os erros que restam são 1–3 caixas (PET como tampa, pote como copo). O custo é a cobertura: só ~29% dos objetos têm consenso.
- **Escolha do peso do primeiro ciclo**: `best.pt` e TACO `s` empatam; fica o `best.pt` (padrão do anotador). A decisão que importa é a da regra (decisão 18), e o caminho para a cobertura é o (c): o YOLO de cada ciclo, retreinado com a base revisada, é o terceiro anotador do ciclo seguinte (T12).

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

**Risco: ajustar as descrições às fotos de validação.** Não há conjunto independente: as quatro validações são as mesmas cenas, e `tcc-teste` tem só 7 fotos (de março, 49 caixas) rotuladas num esquema próprio de 6 classes, não no do TACO. Mitigações:
- poucas iterações de texto, todas registradas aqui com o resultado;
- ajustar com as fotos de 0° (`tcc-0CF`, `tcc-0SF`) e conferir nas de 45°, sabendo que as cenas se repetem;
- confirmar nas primeiras fotos da esteira assim que existirem.

**Decisão**: levar o SigLIP ao `anotar.py` (opção `--classificador`) se ele subir bem o acerto de material, por exemplo em 15 pontos ou mais, e tirar `Glass bottle` dos 7%. Se o zero-shot não separar PET de vidro, o passo seguinte reaproveita os mesmos recortes e embeddings: kNN ou regressão logística sobre as caixas da equipe. A validação desse passo precisa ser por cena, não por cenário. Agrupar as fotos dos quatro cenários por cena (horário e conteúdo) é pré-requisito.

**Esforço**: ~½ dia para o `classificador.py` e a integração ao `avaliar.py`, ~½ dia para os experimentos.

Fontes: [SAM 3 — Ultralytics](https://docs.ultralytics.com/models/sam-3), [Ultralytics 8.3.237](https://newreleases.io/project/pypi/ultralytics/release/8.3.237), [SAM 3 — Transformers](https://huggingface.co/docs/transformers/model_doc/sam3), [Grounding DINO vs YOLOE — Roboflow](https://playground.roboflow.com/models/compare/grounding-dino-vs-yoloe), [Open-vocabulary detection — Fora Soft](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/open-vocabulary-detection-grounding-dino-florence-2-rtdetr-rfdetr). [Instalação do SAM 3](https://www.mintlify.com/facebookresearch/sam3/installation), [RF-DETR — ICLR 2026](https://mlanthology.org/iclr/2026/robinson2026iclr-rfdetr/), [RF-DETR vs. alternativas — Roboflow](https://blog.roboflow.com/rf-detr-vs-alternatives/). Levantamento de 2026-10-27, revisto em 2026-11-12 (SAM 3 e RF-DETR); custos e cabimento na GPU são estimativas, não medidos, salvo onde dito.

## 6. Pipeline de anotação (planejado em 2026-11-11)

O fluxo do diagrama v3, do lado da anotação, em passos separados que se podem rodar um de cada vez ou encadeados por um `pipeline.py`:

```
importar.py lote/   → armazenamento comum (images/); no banco, a imagem com lote, conjunto, metadados
anotar.py × N       → propostas no banco, uma execução por anotador e rodada, um anotador por vez (anotadores.yaml)
treino: votar.py    → aprovadas: labels/ com as caixas de consenso; reprovadas e auditoria: fila de revisão
teste:  votar.py    → caixas sem classe (união dos N), fila de revisão obrigatória (T9; desde 2026-11-15 no votar.py)
revisar.py          → revisão humana
exportar            → treino.txt, teste.txt, data.yaml
```

### Importação (T5)

A fonte prevista é uma só: a webcam da esteira em operação (T4). As imagens chegam ao servidor, e o `importar.py` grava **uma cópia** de cada uma em `images/`, o armazenamento comum de todos os anotadores; o `anotar.py` deixa de copiar e passa a ler só de lá. Se o espaço pesar, a cópia vira link (hardlink no mesmo sistema de arquivos, senão simbólico).

A importação é simples, por decisão (2026-11-11): sem hash, sem análise de conteúdo (nitidez, exposição, quase duplicadas) e sem tratamento especial de metadados, porque todas as imagens vêm da mesma câmera.

| Passo | Muda a imagem? | Por quê |
|---|---|---|
| Nome único | Não (só o nome) | `<lote>_<nome original>`, para lotes diferentes não colidirem; o `stem` continua único (`registrar_imagem`) |
| Girar pelo EXIF | Só se houver orientação no EXIF | Quadros da webcam não têm; fica para fotos de outra origem (validação, celular), em que as caixas têm de valer para a imagem girada. Sem giro, cópia byte a byte: recomprimir um JPEG perde qualidade |
| Reduzir a resolução | Não por padrão | Resolução nativa (T4), para não limitar um modelo que reduza menos que o YOLO (640) ou o Grounding DINO (1333). Opção `--lado-maximo` com um teto folgado, só para fotos grandes de outra origem (as de celular têm 4080×3060, ~8 MB) |

Fora da importação, de propósito:
- **Normalizar cor ou brilho**: afastaria a base de treino dos quadros que o YOLO vê na operação, crus. Variação de cor e brilho é aumento de dados no treino (o Ultralytics já faz), não mudança na base.
- **Recortar a esteira**: a imagem gravada mantém o quadro inteiro, porque é o que a câmera vê na operação. O que está fora da esteira (o papel no fundo branco, seção 5) se resolve com uma **região de interesse** do lote, guardada como metadado: os anotadores descartam as caixas **com o centro fora dela**, e a imagem não muda. A regra é o centro, e não a caixa inteira dentro, para não descartar objeto real na borda da esteira: o YOLO aprenderia esse objeto como fundo. Fora da esteira é fundo fixo (a mesa), então quase toda caixa lá é erro do anotador. A página de revisão desenha a região, para o revisor ver por que uma caixa não aparece.

### Anotadores configuráveis

- **`anotadores.yaml`** (feito em 2026-11-15, com o `pipeline.py`; T14): quais anotadores rodam, com o tipo (`grounding-dino`, `owlv2`, `yoloe`...), a versão do modelo e os parâmetros (limiares, contenção). A pipeline lê dele, o voto registra qual configuração usou (RNF07).
- **Interface genérica de detector**: uma classe base no `anotar.py` cuida de tudo que não depende do modelo (limiar, área máxima, NMS, contenção, candidatas). Um detector novo sobrescreve só o carregamento e a inferência: imagem → caixas brutas com a pontuação de cada classe. Um anotador que só reclassifica (SigLIP) sobrescreve outra etapa, recebendo as caixas de outro.
- **Uma lista só de caixas por proposta**, a partir de um piso baixo (0,05), com a confiança de cada uma. Quem lê aplica o próprio limiar: a página mostra a partir de 0,20, oferece as de baixo como candidatas do clique e esconde a classe abaixo de 0,35; o voto aplica o limiar de cada anotador; o `avaliar.py` varre limiares. O custo de gerar as caixas extras é desprezível (o modelo sempre calcula todas; o filtro é depois); ~10–15 KB por foto. Aproximação: o NMS e a contenção rodam com mais caixas presentes do que rodariam no limiar final; conferir uma vez contra a anotação direta.
- **Candidatas do clique de um anotador só** (o de base), por enquanto. Medir depois se algum gera caixas melhores que os outros.
- **Feito (2026-11-11)**: `avaliar.py` sobre propostas gravadas (seção "`avaliar.py` sobre propostas gravadas" abaixo). Nas 88 fotos, reproduz as medições avulsas desta data (cobertura 92% e 73% de imagens completas em 0,20; classe por faixa; clique em 81%), em meio segundo. Com a contenção, a detecção em 0,35 ficou em precisão 0,50 e recall 0,41 (era 0,48 e 0,42 sem ela).
- **Feito (2026-11-11)**: classe base `Detector` no `anotar.py` (a subclasse implementa `carregar()` e `pontuar()`), opções de detecção comuns, proposta no formato 2 (lista única desde `--piso`, sempre com a classe; `saida.separar()` aplica os limiares de leitura). Conferido nas mesmas 88 fotos, com as saídas brutas guardadas: gravar desde 0,05 e filtrar na leitura dá **o mesmo conjunto de caixas** que filtrar direto, nas 88 imagens, em 0,15, 0,20 e 0,25 (o NMS e a contenção sempre favorecem a mais confiante, então uma caixa abaixo do limiar nunca derruba uma acima dele). As candidatas agora passam pelo mesmo NMS de 0,5 e pela contenção (antes, um NMS de 0,8 só para elas): ~11 por foto em vez de ~50, a 1ª acerta os mesmos 81% dos objetos sem caixa, e as 3 primeiras caem de 87% para 81%.

### `avaliar.py` sobre propostas gravadas

O `avaliar.py` deixa de rodar o modelo: lê as propostas vigentes de um anotador numa saída anotada sobre as fotos de validação (importadas como as outras) e os rótulos da equipe. Mede qualquer anotador pela mesma interface, em segundos e sem GPU, e o voto (T3) é ler N arquivos por foto. Medidas: cobertura sem classe e imagens completas por limiar, caixas a remover, acerto de classe e de material das caixas que cobrem um objeto, precisão e recall. Sai o "não localizadas" sobre as 900 consultas do Grounding DINO: provou que as caixas do modelo eram aproveitáveis, e a cobertura o substitui para qualquer anotador.

### Paralelismo (possível, não necessário)

Na GTX 1650, um anotador por vez, no mesmo processo (carregar, anotar o lote, liberar a memória, o próximo). O formato já permite paralelizar sem mudança:
- **Unidade de trabalho**: (imagem, anotador). Cada anotador grava as suas propostas no banco, uma transação por imagem, e pula o que já tem: N anotadores podem rodar em processos ou GPUs diferentes, e uma rodada interrompida continua de onde parou.
- **O voto espera**: só vota uma imagem com proposta de todos os N anotadores configurados; a incompleta fica para a próxima rodada, não é reprovada.
- **Vários escritores**: `importar.py`, `anotar.py`, `votar.py` e o `revisar.py` gravam no mesmo banco. Desde o SQLite (fase 3b do T1, 2026-11-13), cada gravação é uma transação com a trava de escrita desde o início (`BEGIN IMMEDIATE`), e quem chega depois espera; não é preciso arquivo de trava.

### Voto e revisão

- **O voto usa a classe do anotador, mesmo abaixo de 0,35** (`sugerida`); a classe só é escondida do revisor, quando a imagem vai à revisão.
- **Desvio treino/teste antes do voto**: lote de teste não é votado; vai à união sem classe e à revisão obrigatória (seção 4).
- **Auditoria cega**: as aprovadas sorteadas (5%) entram na fila com o mesmo status das reprovadas; a marca de auditoria fica num campo que a página não mostra.
- **Toda revisão parte de um voto** (2026-11-15): imagem não votada não é revisável, e o `--aceitar` (proposta de um anotador direto como rótulo) saiu.

## Tarefas

| # | Status | Tarefa | Depende de | Verificação |
|---|---|---|---|---|
| T1 | [~] | **Framework de anotação e página de revisão** (escopo atual): anotadores intercambiáveis gravando propostas, página para ver, corrigir e editar, registro da revisão. Plano: [`anotacao/PLANO-REVISAO.md`](anotacao/PLANO-REVISAO.md) | — | as do plano |
| T2 | [~] `b70ac8a` | **Escolha dos anotadores** (seção 5): linha de base do Grounding DINO feita e refeita com o vidro em três classes e os rótulos corrigidos; 60 classes e classe genérica medidas (2026-11-10); cobertura sem classe medida e limiar da anotação em 0,20 (2026-11-11); interface genérica de detector, propostas no formato 2 e `avaliar.py` sobre propostas gravadas, com a cobertura, as faixas e o clique (seção 6, 2026-11-11); OWLv2 como anotador, medido (2026-11-12: classe 75% e material 89%, contra 57% e 65% do Grounding DINO); vários prompts por classe, adotados (2026-11-13: classe do DINO 57% → 63%, do OWLv2 76% → 79%, imagens completas 73% → 86% e 85% → 92%); YOLO da equipe como terceiro anotador, medido (2026-11-13: classe 87%, mas cobre só 43% dos objetos); ficam como alternativas a híbrida com SigLIP e o YOLOE | T1 (interface de anotador) | tabelas do `avaliar.py` |
| T3 | [x] `4341c97` | **`avaliar.py --voto`**: taxa de aprovação e fração das aprovadas corretas por inteiro, para escolher o trio; lê as propostas gravadas dos N anotadores (seção 6). Feito: erro conjunto de classe de um par (`--comparar`, 2026-11-12, seção 5); `--voto` com o NooN estrito por imagem e o consenso por caixa (2026-11-13). Medido: por imagem, 1–5% de aprovação com qualquer YOLO; por caixa, 97–99% certas em ~29% dos objetos. Regra: por imagem (decisão 18) | T2 | pytest com caixas sintéticas; tabelas |
| T4 | [ ] | **Captura na esteira**: o backend grava imagens e logs por lote (banco do diagrama). Ver [resolução e origem das imagens](#resolução-e-origem-das-imagens) | — | teste com a esteira |
| T5 | [x] `ab8e46d` | **`importar.py`**: importa um lote para o armazenamento comum (`images/`) e o registra (hoje no banco SQLite), com `lote`, o sorteio treino/teste (1 lote em 5) e a região de interesse do lote; sem pré-processamento além do nome único e do giro pelo EXIF (seção 6); o `anotar.py` deixa de copiar. Não depende do T4: serve às fotos de validação e de celular | T1 | pytest |
| T6 | [x] | **`votar.py`**: aplica o 3oo3 (seção 3) só nos lotes de treino e com a classe `sugerida`, grava `labels/` das aprovadas com as caixas de consenso, `voto`/`motivo`, `treino.txt`, `teste.txt` e `data.yaml`; vota só imagens com proposta dos N anotadores e registra quais propostas usou; grava no banco SQLite (fase 3b do T1, feita), numa transação. Feito (2026-11-14): tabelas `votacoes`, `votos`, `votos_propostas` e `caixas_voto` (esquema v3, sem migração: banco de outra versão é recusado e recriado; `imagens.lote` obrigatório, toda imagem entra pelo `importar.py`); a aprovada continua `pendente` com `voto = aprovada`, e a revisão humana vale mais que o voto; vota de novo só imagem com proposta nova (ou `--revotar`); `data.yaml` com `val: teste.txt` (a base de teste, anotada por humanos, é a validação do treino; sem ela, não se treina). Conferido na cópia de `tcc-0CF` com Grounding DINO e YOLO: o mesmo resultado do `avaliar.py --voto` (1 de 24 aprovada) | T1, T3, T5 | pytest do voto com caixas sintéticas |
| T7 | [x] | **Revisão do voto na página**: fila só das `falhou`; caixas de consenso e, separadas, as que só um ou dois propuseram, com quem propôs. Feito (2026-11-15): a revisão sempre parte do voto vigente (sem voto, 409); a fila padrão, "a revisar", tem as `falhou` e as de teste, com filtros para as aprovadas, as sem voto, as revisadas e as descartadas; a edição começa com uma caixa por objeto (a união das caixas dos anotadores): consenso, se todos a acharam com a mesma classe, ou conflito, sem classe, com as classes propostas como sugestões na busca (atalhos 1–3, uma por classe, com quem propôs); candidatas de todos os anotadores, sem as repetidas; cada caixa da revisão registra a origem (caixa do voto, proposta ou candidata). Resolve as três pendências antigas (base no primeiro anotador, ordem misturando escalas na edição, registro só da base). Esquema v4 | T1, T6 | pytest da API; teste no Chrome headless |
| T8 | [ ] | **Auditoria**: amostra das aprovadas (ex.: 5%) na fila de revisão, sem o revisor saber | T6, T7 | pytest |
| T9 | [~] | **Modo de teste**: segmentado e sem classe (padrão no teste, seção 4) e sem pré-anotação. Feito (2026-11-15): o `votar.py` grava a união sem classe das caixas dos anotadores nos lotes de teste, e a página a mostra sem classe, confiança nem anotador (nem na fila nem nas camadas). Falta o modo sem pré-anotação | T1, T5 | pytest; teste manual |
| T10 | [ ] | **`metricas.py`** (RF13): taxa de aprovação e motivos, erro das aprovadas pela auditoria, precisão e recall de cada anotador frente à revisão, tempo por imagem e por objeto, taxa de cada tipo de correção | T1, T6, T8 | pytest com registros sintéticos |
| T11 | [ ] | **Novas classes pela página** (RF14): acrescenta no fim do `classes.yaml` e regenera o `data.yaml` | T1 | pytest; teste manual |
| T12 | [ ] | **Fine-tuning do YOLO** com a base de treino; versões fixadas antes (RNF07). O YOLO retreinado no ciclo n é o terceiro anotador do voto no ciclo n+1 (decisão 17). Treinar também o **RF-DETR** (Nano/Small, Apache 2.0) na mesma base, para comparar com o YOLO: é de conjunto fechado (não serve de anotador), feito para transferir a domínios novos, e evita a AGPL da Ultralytics. XL e 2XL ficam fora (licença PML) | T6, T7 | métricas do treino |
| T13 | [ ] | **Avaliação do YOLO** com a base de teste e uma base externa: `best.pt`, o YOLO retreinado e o RF-DETR lado a lado, mais a taxa de quadros na máquina da esteira | T9, T12 | métricas por classe e material; FPS |
| T14 | [x] | **`pipeline.py` e `anotadores.yaml`** (seção 6): importar, anotar com os N anotadores configurados, votar ou unir conforme o conjunto, com unidade de trabalho (imagem, anotador) retomável. Feito (2026-11-15): o `anotadores.yaml` traz o trio (decisão 17) com as opções do `anotar.py` de cada um e o IoU do voto; a pipeline confere tudo antes de importar ou carregar modelo, roda um anotador por vez liberando a memória entre eles, e a votação grava a configuração (RNF07). Retomável porque o `anotar.py` pula as imagens já anotadas pelo anotador e o voto as já votadas. Conferido com os três modelos em duas fotos de `tcc-0CF` (42 s na GTX 1650; a segunda rodada, sem nada a fazer, em 1 s) | T5, T6 | pytest com anotadores sintéticos |

### Resolução e origem das imagens

Anotado em 2026-11-10, para o T4:

- **Hoje nada está fixado.** O backend passa só o índice da câmera ao Ultralytics: a resolução é a padrão do driver (em webcam USB, em geral 640×480), e o YOLO reduz cada quadro a 640 no lado maior (`imgsz` padrão; o `best.pt` treinou com `imgsz: 640`). Não foi conferido com a câmera da esteira.
- **O banco não é da esteira.** As fotos de `legado/database` são de celular (4080×3060, ~9,5 MB cada), e as de `legado/images` são recortes de foto de celular (de ~1650×3200 a 4624×2316). O YOLO as reduz a 640 de qualquer jeito, então o que pesa é a origem: nitidez, ruído, compressão, cor, iluminação, ângulo e distância diferem dos quadros da webcam. O mAP do `best.pt` mede fotos de celular, não a operação.
- **Para o T4**: gravar os quadros como o backend os recebe, na resolução nativa da câmera, sem reduzir (permite testar um `imgsz` maior depois); pôr a largura e a altura da câmera e o `imgsz` no `config.json`, explícitos; registrá-los no log de cada lote.
- **Captura (anotado em 2026-11-11, com a pipeline da seção 6)**:
  - **Quando gravar**: não todo quadro. Quadros seguidos são quase iguais, e cada um a mais custa anotação e revisão sem trazer informação. Por exemplo: gravar quando o YOLO detecta algo na região de interesse, e no máximo um quadro a cada N segundos. Como a importação não analisa conteúdo (seção 6), a redundância se controla aqui.
  - **Resolução**: a maior que a webcam sustenta a uma taxa de quadros aceitável (em geral 1280×720 ou 1920×1080, ~150–400 KB por quadro em JPEG). A importação não recupera resolução que a captura não gravou; o YOLO a 640 não perde, e os anotadores (Grounding DINO até 1333, OWLv2 960) ganham nos objetos pequenos.
  - **Qualidade**: o quadro cru, em JPEG de qualidade alta (95), separado do quadro comprimido que o backend envia pelo WebSocket.
  - **Exposição e balanço de branco fixos** na webcam (sem o automático): estabiliza a imagem na fonte, para o treino e para a operação ao mesmo tempo. É a normalização que vale; normalizar a base depois afastaria o treino da operação (seção 6).
  - **Duas regiões, com nomes diferentes**: a de interesse da anotação (a esteira visível inteira, seção 6) e a faixa de acionamento do backend (`roi_y_min`/`roi_y_max`, quando o servo atua). Ambas podem ficar na configuração da câmera.
- **Validação com a webcam**: os limiares escolhidos nas fotos de celular (0,20, 0,35, 0,05, contenção 0,9) e a escolha do trio têm de ser refeitos com quadros da esteira; a base de teste revisada (T9) passa a cumprir esse papel.
- **Fotos de celular** continuam servindo para comparar anotadores no `avaliar.py`; para treino e teste do YOLO, dão lugar aos quadros da esteira. Quando houver quadros, refazer a linha de base dos anotadores com eles: o Grounding DINO viu fotos de 12 MP, reduzidas a até 1333 no lado maior.

## Decisões do sistema

As decisões que só valem para o framework (ferramenta própria, fonte das classes, um revisor) ficam no plano do T1. Os números são os do plano original.

| # | Questão | Decisão |
|---|---|---|
| 4 | ~~Um anotador ou vários?~~ | **Decidido (2026-10-28)**: três anotadores com voto 3oo3; quem não passa vai à revisão humana (seção 3). |
| 5 | ~~O teste chega ao revisor com as propostas dos anotadores ou sem elas?~~ | **Decidido (2026-10-28)**: segmentado e sem classe. Os objetos chegam delimitados para poupar a seleção; a classe é do revisor (seção 4). |
| 6 | ~~O voto exige a mesma classe ou só o mesmo material?~~ | **Decidido (2026-10-28)**: mesma classe. Por material aprovaria mais, mas a imagem ficaria sem classe definida para o treino. |
| 7 | ~~Proporção treino/teste e unidade do sorteio~~ | **Decidido (2026-10-28)**: sorteio por lote de captura, 1 lote em cada 5 para o teste. Frames seguidos da esteira são quase iguais; sortear imagem a imagem vazaria cenas entre os conjuntos. |
| 13 | ~~Onde as imagens ficam e quem as copia?~~ | **Decidido (2026-11-11)**: o `importar.py` grava uma cópia de cada imagem em `images/`, na resolução nativa e sem normalizar nem recortar (seção 6), e todos os anotadores leem de lá; link em vez de cópia se o espaço pesar. Sem hash nem análise de conteúdo: a fonte é uma só, a webcam da esteira. |
| 14 | ~~Como os anotadores são definidos e medidos?~~ | **Decidido (2026-11-11)**: por `anotadores.yaml`, sobre uma classe base de detector que só exige a inferência; o `avaliar.py` mede propostas gravadas, não roda modelo (seção 6). |
| 15 | ~~A classe abaixo de 0,35 entra no voto?~~ | **Decidido (2026-11-11)**: sim, a `sugerida`; só é escondida do revisor. Candidatas do clique vêm de um anotador só, por enquanto. |
| 16 | ~~Limiar na gravação ou na leitura?~~ | **Decidido (2026-11-11)**: na leitura. A proposta guarda todas as caixas a partir de 0,05, com a confiança, e cada consumidor (página, voto, `avaliar.py`) aplica o seu. |
| 8 | ~~Taxonomia do vidro~~ | **Decidido (2026-11-09)**: três classes TACO, `Glass bottle`, `Glass jar` e `Glass cup` (copos, taças e tigelas). `Glass jar` e `Glass cup` entram no fim do `classes.yaml`, para não mudar os ids. |
| 17 | ~~Quem é o trio do voto?~~ | **Decidido (2026-11-13)**: Grounding DINO, OWLv2 e o YOLO da equipe (`best.pt`). O YOLO é preciso na classe e erra independentemente dos outros dois, mas cobre pouco; a regra do voto (T3) tem de tratar isso (seção 5). A cada ciclo, o YOLO retreinado com a base revisada (T12) passa a ser o terceiro anotador do ciclo seguinte; o `best.pt` (ou o TACO puro, equivalente aqui) é o do primeiro ciclo. |
| 18 | ~~Voto por imagem ou por caixa?~~ | **Decidido (2026-11-13)**: por imagem, o 3oo3 estrito da seção 3. Nas fotos de validação aprova só 1–5% (com ~4 objetos por foto, uma caixa a mais reprova), mas a aposta é que melhore com os quadros da esteira, com menos objetos por vez (T4), e com o YOLO retreinado a cada ciclo (T12). O consenso por caixa (97–99% certas) fica medido no `avaliar.py --voto` para rever a decisão se a aprovação continuar baixa. |
