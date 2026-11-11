# Anotação assistida

Primeiro passo da anotação assistida prevista na monografia (seção 5.3.4, RF11): `anotar.py` propõe caixas para uma ou mais imagens com o [Grounding DINO](https://huggingface.co/IDEA-Research/grounding-dino-tiny), um detector de vocabulário aberto. Ele não depende do detector em operação (`best.pt`), então não herda os erros dele. As caixas são **propostas** para um revisor humano: ficam em `propostas/`, à parte dos rótulos finais em `labels/`.

## Instalação

Num ambiente separado do backend (o torch é grande):

```bash
pip install -r anotacao/requirements.txt
```

No Linux, o torch do PyPI já vem com CUDA; no Windows, ele é só para CPU, e para usar a GPU é preciso instalar antes o torch com CUDA ([pytorch.org](https://pytorch.org/get-started/locally/)). Roda também sem GPU, só que mais devagar. Na primeira execução, os pesos (~700 MB para o `tiny`) são baixados do Hugging Face para `~/.cache/huggingface`.

## Uso

```bash
python anotacao/anotar.py foto.jpg                       # saída em ./anotacoes
python anotacao/anotar.py fotos/*.jpg -o anotacoes --previa
python anotacao/anotar.py -o anotacoes --aceitar         # propostas viram rótulos, sem revisão
```

| Opção | Padrão | |
|---|---|---|
| `-o`, `--saida` | `anotacoes` | Diretório de saída |
| `--anotador` | `grounding-dino` | Qual anotador propõe as caixas (por enquanto, só esse) |
| `--classes` | `anotacao/classes.yaml` | Lista de classes |
| `--dispositivo` | `cuda` se houver | `cuda` ou `cpu` |
| `--previa` | — | Grava também `previa/<anotador>/<nome>.jpg` com as caixas desenhadas |
| `--confianca-classe` | `0.35` | Caixas com confiança abaixo dessa são propostas **sem classe**: o revisor tem de dar a classe ou remover a caixa. `0` desliga |
| `--sobrescrever` | — | Anota de novo imagens que já têm proposta deste anotador |
| `--aceitar` | — | Copia as propostas do anotador para `labels/` como estão e marca as imagens como `revisada`; só mexe nas `pendente`, e deixa pendentes as que têm caixa sem classe. Com imagens na linha de comando, aceita só elas, depois de anotá-las; sem, todas as pendentes |

Opções do `grounding-dino`:

| Opção | Padrão | |
|---|---|---|
| `--modelo` | `IDEA-Research/grounding-dino-tiny` | Também `IDEA-Research/grounding-dino-base`, mais preciso e mais lento |
| `--confianca` | `0.2` | Confiança mínima por caixa. Baixa de propósito: cobre 92% dos objetos e sobram ~4 caixas por imagem para remover (medida no `OBJETIVO.md`, seção 5) |
| `--iou` | `0.5` | Caixas que se sobrepõem mais que isso viram uma só, qualquer que seja a classe |
| `--area-maxima` | `0.5` | Descarta caixas maiores que essa fração da imagem (o modelo costuma propor uma caixa para a esteira inteira) |
| `--candidatas` | `0.05` | Grava também, sem classe, as caixas brutas do modelo com confiança a partir dessa, para a caixa por clique na página de revisão (cerca de 50 por foto, ~6 KB). `1` desliga |
| `--contencao` | `0.9` | Remove a caixa que tem ao menos essa fração dentro de outra maior e mais confiante (partes do objeto, como o topo da lata proposto como tampa, e duplicatas menores, que o NMS não pega). A caixa grande que envolve uma menor mais confiante fica: em geral é o objeto inteiro. Acima de `1` desliga |

## Google Colab

Sem GPU no computador, use o notebook [`anotar_colab.ipynb`](anotar_colab.ipynb) ([abrir no Colab](https://colab.research.google.com/github/vdlwang/ecovision-iterativo/blob/main/anotacao/anotar_colab.ipynb)). Ele clona o repositório e roda o próprio `anotar.py`, com as opções acima em formulário; as fotos podem vir do Google Drive ou ser enviadas do computador, e a saída fica no Drive (ou é baixada como `.zip`). Imagens que já têm proposta na saída são puladas, então, se o Colab desconectar, basta rodar de novo. O campo `RAMO` escolhe o ramo clonado.

## Saída

```
anotacoes/
├── data.yaml                          # names: os nomes de classes.yaml (TACO + Background); train e val: revisadas.txt
├── images/foto.jpg
├── propostas/grounding-dino/foto.json # o que o anotador propôs, com a confiança
├── labels/foto.txt                    # rótulos finais (YOLO): só depois da revisão ou de --aceitar
├── revisoes/foto.json                 # registro da última revisão (tempo, desfecho de cada caixa)
├── imagens.csv                        # nome e status de cada imagem: pendente, revisada, descartada
├── revisadas.txt                      # imagens revisadas com rótulo; gerado de imagens.csv
├── previa/grounding-dino/foto.jpg     # só com --previa
└── visualizar.html                    # página para conferir propostas e rótulos (abaixo)
```

As propostas ficam separadas dos rótulos por dois motivos. O Ultralytics trata imagem sem objetos como fundo, então uma imagem não revisada com `.txt` entraria no treino como negativo falso. E, sem a proposta original, não dá para medir quanto o revisor corrigiu cada anotador (RF13). Por isso o `data.yaml` aponta para `revisadas.txt`, e não para `images/`.

Cada proposta é um JSON:

```json
{"anotador": "grounding-dino", "versao": "IDEA-Research/grounding-dino-tiny",
 "parametros": {"confianca": 0.2, "iou": 0.5, "area_maxima": 0.5, "contencao": 0.9,
                "confianca_classe": 0.35},
 "classes": "<hash da lista de classes>", "imagem": "foto.jpg", "largura": 4032, "altura": 3024,
 "caixas": [{"classe": "Drink can", "confianca": 0.81, "caixa": [x1, y1, x2, y2]},
            {"classe": null, "sugerida": "Glass cup", "confianca": 0.22, "caixa": [x1, y1, x2, y2]}],
 "candidatas": [{"confianca": 0.12, "caixa": [x1, y1, x2, y2]}]}
```

A classe vai pelo nome, e a caixa em pixels da imagem gravada em `images/`. Abaixo de `--confianca-classe`, a caixa vai sem classe (`null`); a classe do anotador fica em `sugerida`, que as páginas não mostram (serve às métricas). Cada anotador grava na sua pasta, então vários podem anotar a mesma saída, um de cada vez. Uma imagem entra em `imagens.csv` como `pendente`, e anotar de novo não muda o status dela. Os rótulos em `labels/` usam o formato de detecção do YOLO (`id cx cy w h`, de 0 a 1), e uma imagem revisada sem objetos tem `.txt` vazio (fundo).

Várias execuções podem gravar no mesmo diretório. Se o `data.yaml` da saída tiver outras classes, o script o refaz quando nenhum `.txt` de `labels/` nem registro de `revisoes/` guarda ids (as propostas guardam a classe pelo nome; fundo e descarte não têm caixas); senão, recusa a saída, porque os ids deixariam de bater. Recusa também uma saída do formato antigo (`labels/` sem `imagens.csv`), em que as propostas eram gravadas direto como rótulos. Se o EXIF da foto pede rotação (fotos de celular), a imagem é gravada já girada, e as caixas valem para ela.

Ainda não há divisão entre treino e validação: ela deve ser feita por sessão de captura, nunca por imagem (monografia, seção 5.3.5), e fica para quando houver sessões.

O diretório `anotacoes/` está no `.gitignore`: imagens não vão para o repositório (RNF10).

## Visualização

Ao terminar, o `anotar.py` grava `visualizar.html` no diretório de saída e imprime o endereço. A página abre direto no navegador, sem servidor. À esquerda fica a lista das imagens, com a contagem de objetos e o status. À direita, a imagem com as caixas coloridas por classe e, embaixo, a contagem por classe. O seletor "mostrar" escolhe o que é desenhado:

- **automático** (padrão): a anotação final se a imagem tem `.txt`; senão, as propostas do primeiro anotador que tiver alguma;
- **anotação final**: só `labels/`;
- **propostas: \<anotador\>**: as propostas de um anotador.

As propostas aparecem tracejadas e com a confiança, e as caixas finais em linha contínua. As setas `←`/`→` navegam, as caixas e os nomes podem ser escondidos, e `visualizar.html#3` abre a terceira imagem. A página só mostra; corrigir fica para a página de revisão (RF12, [`PLANO-REVISAO.md`](PLANO-REVISAO.md)).

A página lê os arquivos quando é gerada. Depois de editar algum à mão, ou para ver um diretório no formato YOLO gerado por outra ferramenta (só `data.yaml`, `images/` e `labels/`), gere de novo:

```bash
python anotacao/visualizar.py anotacoes
```

## Revisão

`revisar.py` serve uma página local de revisão sobre um diretório do `anotar.py`, sem dependência além das do script:

```bash
python anotacao/revisar.py anotacoes --abrir      # http://127.0.0.1:8000/
python anotacao/revisar.py anotacoes --porta 8001
```

A página mostra a fila das imagens `pendente`, das mais incertas para as mais seguras: a ordem é pela menor confiança entre as caixas propostas, e as imagens sem nenhuma caixa vêm primeiro, porque são as que mais podem ter objeto não achado. Os filtros trocam o status (`revisada`, `descartada`, todas) e a ordem (por nome). As setas `←`/`→` andam pela fila, e `#<nome da imagem>` no endereço abre aquela imagem.

### Edição

Numa imagem `pendente`, com "mostrar" em "automático (edição)", as caixas propostas pelo anotador (o primeiro em ordem alfabética, se houver vários) podem ser corrigidas. Proposta intocada aparece tracejada, com a confiança; caixa corrigida, em linha contínua. Caixa proposta sem classe (confiança baixa) aparece em vermelho como "sem classe": a imagem só pode ser salva depois que cada uma recebe classe ou é removida.

| Ação | Mouse | Teclado |
|---|---|---|
| Selecionar caixa | clique (já abre a busca) | `Tab` / `Shift+Tab`, em ordem de leitura |
| Trocar a classe | escrever no campo de busca e clicar na opção | com a caixa selecionada, escrever (a primeira letra já abre a busca); `↑`/`↓` e `Enter` escolhem |
| Trocar para uma classe do anotador | — | `1`–`9`, na ordem de `classes` no `classes.yaml` |
| Remover caixa | "Remover caixa" | `Del` |
| Desfazer a seleção | clique fora das caixas | `Esc` |
| Desfazer e refazer | — | `Ctrl+Z`; `Ctrl+Shift+Z` ou `Ctrl+Y` (`Cmd` no Mac). Valem para trocar classe, remover e adicionar caixa, na imagem atual; na busca com texto, ficam com o campo |
| Nova caixa por clique | "Nova caixa" e um clique no objeto | `N` (sem caixa selecionada), clique no objeto, `Tab`/`Shift+Tab` ou a roda do mouse trocam a candidata, `Enter` confirma, `Esc` cancela |
| Salvar e ir para a próxima | "Salvar e próxima" | `Enter`, que pede confirmação (`Enter` confirma, `Esc` cancela); `Ctrl+S` (`Cmd+S` no Mac) salva direto, também com a busca aberta |
| Descartar a imagem (inútil para treino) | "Descartar imagem" | `D` sem caixa selecionada (com uma selecionada, o `d` vai para a busca); sempre pede confirmação |

O `Tab` segue a ordem de leitura pelos centros das caixas: linhas de cima para baixo e, em cada linha, da esquerda para a direita. Uma caixa entra na linha atual se o centro dela cai na faixa vertical da primeira caixa da linha, a mais alta. O campo de busca mostra a posição da caixa nessa ordem ("caixa 2 de 7").

A busca oferece qualquer classe do `data.yaml` e mostra até 9 opções. Não diferencia maiúsculas nem acentos e casa, nesta ordem: o início do nome, o início de uma palavra ("can" → `Drink can`), as iniciais ("cpb" → `Clear plastic bottle`), um trecho qualquer e o material, em português ou inglês ("vidro" → as classes de vidro do anotador; só elas têm material). Nos empates, vêm antes as classes usadas há pouco e as do anotador. Com o campo vazio, a lista mostra essas mesmas. Na busca, `Esc` fecha sem trocar e `Tab` passa para a caixa seguinte.

A confirmação do `Enter` resume o que vai ser gravado: as classes das caixas, quantas foram corrigidas e removidas, e o aviso de fundo quando não sobra nenhuma caixa. Salvar pelo botão ou por `Ctrl+S` não pede confirmação.

Salvar sem mudar nada aceita as propostas como estão. Salvar uma imagem sem caixas a grava como fundo (`.txt` vazio). Salvar grava `labels/<nome>.txt` e marca a imagem como `revisada`; descartar apaga o `.txt`, se houver, e a marca como `descartada`. Nos dois casos, a imagem sai da fila de pendentes. Trocar de imagem com alterações não salvas pede confirmação.

**Nova caixa por clique.** Para um objeto sem caixa: `N`, depois um clique no objeto. A página mostra, tracejada em branco, a candidata mais confiante que contém o ponto, entre as gravadas pelo `anotar.py` (`--candidatas`); as quase iguais a uma caixa já presente (IoU ≥ 0,9) ficam de fora. `Tab` ou a roda passam às seguintes; `Enter` confirma, e a caixa nasce sem classe, com a busca já aberta. Se nenhuma candidata servir, clique em outra parte do objeto. Propostas gravadas antes das candidatas não têm nenhuma: anote de novo.

Desfazer tudo volta às propostas como chegaram, e a imagem deixa de contar como alterada. Ainda não dá para desenhar à mão, mover ou redimensionar caixas: um objeto que nenhuma candidata cobre leva ao descarte da imagem (decisão 12 do `PLANO-REVISAO.md`). Também não dá para reabrir uma imagem revisada ou descartada (fase 5): as outras camadas e status são só para ver.

Cada revisão grava `revisoes/<nome>.json` (RF13), sobrescrito se a imagem for revisada de novo:

```json
{"imagem": "foto.jpg", "acao": "salvar", "data": "2026-11-10T00:13:30-03:00",
 "tempo_ativo_s": 6.0, "revisor": null,
 "base": {"anotador": "grounding-dino", "versao": "IDEA-Research/grounding-dino-tiny", "classes": "<hash>"},
 "caixas": [{"id": 2, "caixa": [x1, y1, x2, y2], "proposta": 0, "desfecho": "classe_corrigida"}],
 "removidas": [1]}
```

O desfecho de cada caixa (`aceita`, `classe_corrigida`, `classe_atribuida` para proposta sem classe, `adicionada`) é calculado pelo servidor frente à proposta de origem; uma caixa adicionada por clique leva `"origem": "candidata"`, e o servidor confere que ela é mesmo uma das candidatas do anotador de base, e `removidas` lista os índices das propostas apagadas. O tempo ativo só conta com a aba visível e em foco, e pausa depois de 60 s sem interação.

### Servidor e API

O servidor escuta só em `127.0.0.1` e lê o disco a cada pedido, então mudanças feitas à mão aparecem ao recarregar. Gravações aceitam só o `Host` local, para que um site aberto no navegador não consiga gravar pela porta (DNS rebinding). A API, em JSON, é a mesma que a página usa:

| Rota | Resposta |
|---|---|
| `GET /api/classes` | `[{id, nome, material}]` |
| `GET /api/imagens?status=pendente&ordem=incerteza` | `{imagens: [{nome, status, anotadores, n_caixas, confianca_min, tem_final}], anotadores, contagem}` |
| `GET /api/imagens/<nome>` | `{nome, status, largura, altura, final, propostas: {anotador: [...]}, invalidas, revisao}` |
| `PUT /api/imagens/<nome>` | Recebe `{acao: "salvar" \| "descartar", base, tempo_ativo_s, caixas: [{id, caixa, proposta}]}` e devolve o mesmo que o `GET`. 400 para pedido inválido (nada é gravado), 409 se a imagem não está pendente |
| `GET /images/<nome>` | A imagem |

As caixas vão como `{id, nome, conf, caixa: [x1, y1, x2, y2]}`, normalizadas de 0 a 1, com `conf` nula na anotação final e `id` nulo para classe fora do `data.yaml`. No `PUT`, `proposta` é o índice da caixa de origem nas propostas de `base`, ou `null` para uma caixa nova. Só imagens que estão no `imagens.csv` são servidas. A gravação segue a ordem `labels/`, `revisoes/` e, por último, o status em `imagens.csv`: interrompida no meio, a imagem continua pendente.

## Novo anotador

Um anotador é uma classe em `anotar.py`, registrada no dicionário `ANOTADORES`, com:

- `nome`: o valor de `--anotador` e a pasta em `propostas/`;
- `opcoes(parser)`: acrescenta as opções de linha de comando dele (de preferência num grupo com o nome dele);
- `criar(classes, args)`: constrói o anotador a partir das classes de `classes.yaml` e das opções;
- na instância, `versao` e `parametros`, gravados em cada proposta, e `anotar(imagem)`, que recebe a imagem PIL em RGB e devolve `[(id da classe, confiança, (x1, y1, x2, y2) normalizada de 0 a 1)]`.

O que cada um faz com o `prompt` das classes é dele. `GroundingDino` é o exemplo.

## Classes

`classes.yaml` tem duas listas (nível 2 da taxonomia):

- `nomes`: as classes dos rótulos. O índice é o id nos `.txt`, e o `data.yaml` de cada saída é gerado dela. São as 60 classes TACO e `Background`, na ordem de `legado/database/tcc-*/YOLO_dataset/data.yaml` e do `yolo_models/taco/best.pt`, para que as anotações sirvam direto ao fine-tuning dele. Para não invalidar anotações já feitas, só acrescente no fim.
- `classes`: o que o anotador automático procura, um subconjunto de `nomes`, cada uma com o `nome`, o `prompt` em inglês enviado ao modelo e o `material` (nível 1). A ordem dela não muda os ids. A lista inicial são as seis classes TACO das fotos da equipe, mais `Glass jar` e `Glass cup`: o vidro é dividido em garrafas, potes e copos (decisão 8 do [`OBJETIVO.md`](../OBJETIVO.md)).

Na revisão, qualquer classe de `nomes` pode ser escolhida, mesmo as que o anotador não procura.

Uma classe de `classes` com `reserva: true` só vence numa caixa quando nenhuma das outras chega ao limiar de confiança. Serve para uma classe genérica (por exemplo, `Unlabeled litter` com o prompt "object") dar caixa aos objetos que as outras não reconhecem, sem tirar delas os que reconhecem. Nenhuma classe a usa por enquanto: a frase a mais no prompt muda a pontuação das outras (medição na seção 5 do [`OBJETIVO.md`](../OBJETIVO.md)).

O prompt é o que mais muda o resultado. Prefira descrições visuais curtas ("cardboard box" em vez de "corrugated carton"), e use `--previa` para conferir.

Como cada caixa recebe uma classe: o Grounding DINO dá uma pontuação por token do texto; a confiança de uma classe é a maior entre os tokens do seu prompt, e vence a classe de maior confiança.

## Avaliação

`avaliar.py` mede o anotador nas fotos rotuladas pela equipe (por padrão, as 88 imagens das quatro validações de `legado/database`, 375 caixas nas classes de `classes.yaml`):

```bash
python anotacao/avaliar.py                                   # Grounding DINO tiny
python anotacao/avaliar.py --modelo IDEA-Research/grounding-dino-base
python anotacao/avaliar.py legado/database/tcc-0CF/YOLO_dataset/validation
```

São duas medidas. A **classificação** pega, para cada caixa verdadeira, a caixa do modelo que mais se sobrepõe a ela e compara as classes: mostra a matriz de confusão, a taxa de acerto da classe e a do material, sem misturar com erros de localização. A **detecção** roda o `anotar.py` completo em vários limiares de confiança (`--limiares`) e dá precisão e recall, contando como acerto IoU ≥ 0,5 com a mesma classe.

Os rótulos da equipe usam nomes TACO; entram só as classes que estão em `classes.yaml`, casadas pelo nome, e os polígonos viram a caixa que os contém. Antes disso, o `avaliar.py` aplica [`correcoes_rotulos.yaml`](correcoes_rotulos.yaml): a equipe rotulou todo vidro como `Glass bottle`, e as 97 caixas são, na verdade, potes, copos, taças, tigelas e 3 latas. O arquivo indica a linha de cada `.txt` e confere a classe original; `legado/` não é editado. `--sem-correcoes` usa os rótulos como estão, e `--correcoes` aponta para outro arquivo. As quatro validações são as mesmas cenas fotografadas de jeitos diferentes, então somá-las não equivale a quatro vezes mais dados; serve para comparar anotadores, que não treinaram nelas.

## Próximos passos

O plano do framework de anotação e da página de revisão (escopo atual) está em [`PLANO-REVISAO.md`](PLANO-REVISAO.md); o sistema completo, com voto entre anotadores e bases de treino e teste, em [`OBJETIVO.md`](../OBJETIVO.md).

## Testes

```bash
python -m pytest anotacao/tests     # não carregam o modelo; precisam de pytest, pyyaml e pillow
```
