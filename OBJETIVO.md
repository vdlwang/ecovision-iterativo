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

## 6. Pipeline de anotação (planejado em 2026-11-11)

O fluxo do diagrama v3, do lado da anotação, em passos separados que se podem rodar um de cada vez ou encadeados por um `pipeline.py`:

```
importar.py lote/   → armazenamento comum (images/), imagens.csv com lote, conjunto, metadados
anotar.py × N       → propostas/<anotador>/<nome>.json, um anotador por vez (anotadores.yaml)
treino: votar.py    → aprovadas: labels/ com as caixas de consenso; reprovadas e auditoria: fila de revisão
teste:  unir.py     → caixas sem classe (união dos N), fila de revisão obrigatória (T9)
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

- **`anotadores.yaml`**: quais anotadores rodam, com o tipo (`grounding-dino`, `owlv2`, `yoloe`...), a versão do modelo e os parâmetros (limiares, contenção). A pipeline lê dele, o voto registra qual configuração usou (RNF07).
- **Interface genérica de detector**: uma classe base no `anotar.py` cuida de tudo que não depende do modelo (limiar, área máxima, NMS, contenção, candidatas). Um detector novo sobrescreve só o carregamento e a inferência: imagem → caixas brutas com a pontuação de cada classe. Um anotador que só reclassifica (SigLIP) sobrescreve outra etapa, recebendo as caixas de outro.
- **Uma lista só de caixas por proposta**, a partir de um piso baixo (0,05), com a confiança de cada uma. Quem lê aplica o próprio limiar: a página mostra a partir de 0,20, oferece as de baixo como candidatas do clique e esconde a classe abaixo de 0,35; o voto aplica o limiar de cada anotador; o `avaliar.py` varre limiares. O custo de gerar as caixas extras é desprezível (o modelo sempre calcula todas; o filtro é depois); ~10–15 KB por foto. Aproximação: o NMS e a contenção rodam com mais caixas presentes do que rodariam no limiar final; conferir uma vez contra a anotação direta.
- **Candidatas do clique de um anotador só** (o de base), por enquanto. Medir depois se algum gera caixas melhores que os outros.

### `avaliar.py` sobre propostas gravadas

O `avaliar.py` deixa de rodar o modelo: lê `propostas/<anotador>/` de uma saída anotada sobre as fotos de validação (importadas como as outras) e os rótulos da equipe. Mede qualquer anotador pela mesma interface, em segundos e sem GPU, e o voto (T3) é ler N arquivos por foto. Medidas: cobertura sem classe e imagens completas por limiar, caixas a remover, acerto de classe e de material das caixas que cobrem um objeto, precisão e recall. Sai o "não localizadas" sobre as 900 consultas do Grounding DINO: provou que as caixas do modelo eram aproveitáveis, e a cobertura o substitui para qualquer anotador.

### Paralelismo (possível, não necessário)

Na GTX 1650, um anotador por vez, no mesmo processo (carregar, anotar o lote, liberar a memória, o próximo). O formato já permite paralelizar sem mudança:
- **Unidade de trabalho**: (imagem, anotador). Cada anotador grava só em `propostas/<anotador>/`, com gravação atômica, e pula o que já tem: N anotadores podem rodar em processos ou GPUs diferentes, e uma rodada interrompida continua de onde parou.
- **O voto espera**: só vota uma imagem com proposta de todos os N anotadores configurados; a incompleta fica para a próxima rodada, não é reprovada.
- **Um escritor por vez no `imagens.csv`**: `importar.py`, `votar.py` e o `revisar.py` escrevem nele. Até o SQLite (fase 3b do T1), um arquivo de trava enquanto a pipeline escreve, e o `revisar.py` recusa gravar enquanto ele existir.

### Voto e revisão

- **O voto usa a classe do anotador, mesmo abaixo de 0,35** (`sugerida`); a classe só é escondida do revisor, quando a imagem vai à revisão.
- **Desvio treino/teste antes do voto**: lote de teste não é votado; vai à união sem classe e à revisão obrigatória (seção 4).
- **Auditoria cega**: as aprovadas sorteadas (5%) entram na fila com o mesmo status das reprovadas; a marca de auditoria fica num campo que a página não mostra.
- **`--aceitar`** vira um caso particular (voto de um anotador só): fica para testes, fora da pipeline.

## Tarefas

| # | Status | Tarefa | Depende de | Verificação |
|---|---|---|---|---|
| T1 | [~] | **Framework de anotação e página de revisão** (escopo atual): anotadores intercambiáveis gravando propostas, página para ver, corrigir e editar, registro da revisão. Plano: [`anotacao/PLANO-REVISAO.md`](anotacao/PLANO-REVISAO.md) | — | as do plano |
| T2 | [~] `b70ac8a` | **Escolha dos anotadores** (seção 5): linha de base do Grounding DINO feita e refeita com o vidro em três classes e os rótulos corrigidos; 60 classes e classe genérica medidas (2026-11-10); cobertura sem classe medida e limiar da anotação em 0,20 (2026-11-11); faltam o `avaliar.py` sobre propostas gravadas, com a cobertura (seção 6), a interface genérica de detector, vários prompts por classe, a híbrida com SigLIP, OWLv2 e YOLOE como anotadores do T1 | T1 (interface de anotador) | tabelas do `avaliar.py` |
| T3 | [ ] | **`avaliar.py --voto`**: taxa de aprovação e fração das aprovadas corretas por inteiro, para escolher o trio; lê as propostas gravadas dos N anotadores (seção 6) | T2 | pytest com caixas sintéticas; tabelas |
| T4 | [ ] | **Captura na esteira**: o backend grava imagens e logs por lote (banco do diagrama). Ver [resolução e origem das imagens](#resolução-e-origem-das-imagens) | — | teste com a esteira |
| T5 | [ ] | **`importar.py`**: importa um lote para o armazenamento comum (`images/`) e o `imagens.csv`, com `lote`, o sorteio treino/teste (1 lote em 5) e a região de interesse do lote; sem pré-processamento além do nome único e do giro pelo EXIF (seção 6); o `anotar.py` deixa de copiar. Não depende do T4: serve às fotos de validação e de celular | T1 | pytest |
| T6 | [ ] | **`votar.py`**: aplica o 3oo3 (seção 3) só nos lotes de treino e com a classe `sugerida`, grava `labels/` das aprovadas com as caixas de consenso, `voto`/`motivo`, `treino.txt`, `teste.txt` e `data.yaml`; vota só imagens com proposta dos N anotadores; trava do `imagens.csv` (seção 6) | T1, T3, T5 | pytest do voto com caixas sintéticas |
| T7 | [ ] | **Revisão do voto na página**: fila só das `falhou`; caixas de consenso e, separadas, as que só um ou dois propuseram, com quem propôs | T1, T6 | pytest da API; teste manual |
| T8 | [ ] | **Auditoria**: amostra das aprovadas (ex.: 5%) na fila de revisão, sem o revisor saber | T6, T7 | pytest |
| T9 | [ ] | **Modo de teste**: segmentado e sem classe (padrão no teste, seção 4) e sem pré-anotação | T1, T5 | pytest; teste manual |
| T10 | [ ] | **`metricas.py`** (RF13): taxa de aprovação e motivos, erro das aprovadas pela auditoria, precisão e recall de cada anotador frente à revisão, tempo por imagem e por objeto, taxa de cada tipo de correção | T1, T6, T8 | pytest com registros sintéticos |
| T11 | [ ] | **Novas classes pela página** (RF14): acrescenta no fim do `classes.yaml` e regenera o `data.yaml` | T1 | pytest; teste manual |
| T12 | [ ] | **Fine-tuning do YOLO** com a base de treino; versões fixadas antes (RNF07) | T6, T7 | métricas do treino |
| T13 | [ ] | **Avaliação do YOLO** com a base de teste e uma base externa | T9, T12 | métricas por classe e material |
| T14 | [ ] | **`pipeline.py` e `anotadores.yaml`** (seção 6): importar, anotar com os N anotadores configurados, votar ou unir conforme o conjunto, com unidade de trabalho (imagem, anotador) retomável | T5, T6 | pytest com anotadores sintéticos |

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
