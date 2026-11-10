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
| `--sobrescrever` | — | Anota de novo imagens que já têm proposta deste anotador |
| `--aceitar` | — | Copia as propostas do anotador para `labels/` como estão e marca as imagens como `revisada`; só mexe nas `pendente`. Com imagens na linha de comando, aceita só elas, depois de anotá-las; sem, todas as pendentes |

Opções do `grounding-dino`:

| Opção | Padrão | |
|---|---|---|
| `--modelo` | `IDEA-Research/grounding-dino-tiny` | Também `IDEA-Research/grounding-dino-base`, mais preciso e mais lento |
| `--confianca` | `0.35` | Confiança mínima por caixa |
| `--iou` | `0.5` | Caixas que se sobrepõem mais que isso viram uma só, qualquer que seja a classe |
| `--area-maxima` | `0.5` | Descarta caixas maiores que essa fração da imagem (o modelo costuma propor uma caixa para a esteira inteira) |

## Google Colab

Sem GPU no computador, use o notebook [`anotar_colab.ipynb`](anotar_colab.ipynb) ([abrir no Colab](https://colab.research.google.com/github/vdlwang/ecovision-iterativo/blob/main/anotacao/anotar_colab.ipynb)). Ele clona o repositório e roda o próprio `anotar.py`, com as opções acima em formulário; as fotos podem vir do Google Drive ou ser enviadas do computador, e a saída fica no Drive (ou é baixada como `.zip`). Imagens que já têm proposta na saída são puladas, então, se o Colab desconectar, basta rodar de novo. O campo `RAMO` escolhe o ramo clonado.

## Saída

```
anotacoes/
├── data.yaml                          # names na ordem de classes.yaml; train e val: revisadas.txt
├── images/foto.jpg
├── propostas/grounding-dino/foto.json # o que o anotador propôs, com a confiança
├── labels/foto.txt                    # rótulos finais (YOLO): só depois da revisão ou de --aceitar
├── imagens.csv                        # nome e status de cada imagem: pendente, revisada, descartada
├── revisadas.txt                      # imagens revisadas com rótulo; gerado de imagens.csv
├── previa/grounding-dino/foto.jpg     # só com --previa
└── visualizar.html                    # página para conferir propostas e rótulos (abaixo)
```

As propostas ficam separadas dos rótulos por dois motivos. O Ultralytics trata imagem sem objetos como fundo, então uma imagem não revisada com `.txt` entraria no treino como negativo falso. E, sem a proposta original, não dá para medir quanto o revisor corrigiu cada anotador (RF13). Por isso o `data.yaml` aponta para `revisadas.txt`, e não para `images/`.

Cada proposta é um JSON:

```json
{"anotador": "grounding-dino", "versao": "IDEA-Research/grounding-dino-tiny",
 "parametros": {"confianca": 0.35, "iou": 0.5, "area_maxima": 0.5},
 "classes": "<hash da lista de classes>", "imagem": "foto.jpg", "largura": 4032, "altura": 3024,
 "caixas": [{"classe": "Drink can", "confianca": 0.81, "caixa": [x1, y1, x2, y2]}]}
```

A classe vai pelo nome, e a caixa em pixels da imagem gravada em `images/`. Cada anotador grava na sua pasta, então vários podem anotar a mesma saída, um de cada vez. Uma imagem entra em `imagens.csv` como `pendente`, e anotar de novo não muda o status dela. Os rótulos em `labels/` usam o formato de detecção do YOLO (`id cx cy w h`, de 0 a 1), e uma imagem revisada sem objetos tem `.txt` vazio (fundo).

Várias execuções podem gravar no mesmo diretório. O script recusa a saída se o `data.yaml` dela tiver outras classes, porque os ids deixariam de bater, e recusa também uma saída do formato antigo (`labels/` sem `imagens.csv`), em que as propostas eram gravadas direto como rótulos. Se o EXIF da foto pede rotação (fotos de celular), a imagem é gravada já girada, e as caixas valem para ela.

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

A página mostra a fila das imagens `pendente`, das mais incertas para as mais seguras: a ordem é pela menor confiança entre as caixas propostas, e as imagens sem nenhuma caixa vêm primeiro, porque são as que mais podem ter objeto não achado. Os filtros trocam o status (`revisada`, `descartada`, todas) e a ordem (por nome). A imagem aparece como no `visualizar.html`, com o mesmo seletor "mostrar". As setas `←`/`→` andam pela fila, e `#<nome da imagem>` no endereço abre aquela imagem.

O servidor escuta só em `127.0.0.1` e lê o disco a cada pedido, então mudanças feitas à mão aparecem ao recarregar. **Por enquanto, a página só mostra.** Corrigir, salvar e descartar são a fase 3 do [`PLANO-REVISAO.md`](PLANO-REVISAO.md).

A API, em JSON, é a mesma que a página usa:

| Rota | Resposta |
|---|---|
| `GET /api/classes` | `[{id, nome, material}]` |
| `GET /api/imagens?status=pendente&ordem=incerteza` | `{imagens: [{nome, status, anotadores, n_caixas, confianca_min, tem_final}], anotadores, contagem}` |
| `GET /api/imagens/<nome>` | `{nome, status, largura, altura, final, propostas: {anotador: [...]}, invalidas, revisao}` |
| `GET /images/<nome>` | A imagem |

As caixas vão como `{id, nome, conf, caixa: [x1, y1, x2, y2]}`, normalizadas de 0 a 1, com `conf` nula na anotação final e `id` nulo para classe fora do `data.yaml`. Só imagens que estão no `imagens.csv` são servidas.

## Novo anotador

Um anotador é uma classe em `anotar.py`, registrada no dicionário `ANOTADORES`, com:

- `nome`: o valor de `--anotador` e a pasta em `propostas/`;
- `opcoes(parser)`: acrescenta as opções de linha de comando dele (de preferência num grupo com o nome dele);
- `criar(classes, args)`: constrói o anotador a partir das classes de `classes.yaml` e das opções;
- na instância, `versao` e `parametros`, gravados em cada proposta, e `anotar(imagem)`, que recebe a imagem PIL em RGB e devolve `[(id da classe, confiança, (x1, y1, x2, y2) normalizada de 0 a 1)]`.

O que cada um faz com o `prompt` das classes é dele. `GroundingDino` é o exemplo.

## Classes

`classes.yaml` lista as classes (nível 2 da taxonomia), cada uma com o `nome` gravado no `data.yaml`, o `prompt` em inglês enviado ao modelo e o `material` (nível 1). A lista inicial são as seis classes TACO das fotos da equipe. O índice na lista é o id da classe nos `.txt`: para não invalidar anotações já feitas, só acrescente classes no fim.

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

Os rótulos da equipe usam nomes TACO; entram só as classes que estão em `classes.yaml`, casadas pelo nome, e os polígonos viram a caixa que os contém. As quatro validações são as mesmas cenas fotografadas de jeitos diferentes, então somá-las não equivale a quatro vezes mais dados; serve para comparar anotadores, que não treinaram nelas.

## Próximos passos

O plano do framework de anotação e da página de revisão (escopo atual) está em [`PLANO-REVISAO.md`](PLANO-REVISAO.md); o sistema completo, com voto entre anotadores e bases de treino e teste, em [`OBJETIVO.md`](../OBJETIVO.md).

## Testes

```bash
python -m pytest anotacao/tests     # não carregam o modelo; precisam de pytest, pyyaml e pillow
```
