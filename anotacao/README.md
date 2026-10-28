# Anotação assistida

Primeiro passo da anotação assistida prevista na monografia (seção 5.3.4, RF11): `anotar.py` propõe caixas para uma ou mais imagens com o [Grounding DINO](https://huggingface.co/IDEA-Research/grounding-dino-tiny), um detector de vocabulário aberto. Ele não depende do detector em operação (`best.pt`), então não herda os erros dele. As caixas são **propostas** para um revisor humano, não rótulos finais.

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
```

| Opção | Padrão | |
|---|---|---|
| `-o`, `--saida` | `anotacoes` | Diretório de saída |
| `--classes` | `anotacao/classes.yaml` | Lista de classes |
| `--modelo` | `IDEA-Research/grounding-dino-tiny` | Também `IDEA-Research/grounding-dino-base`, mais preciso e mais lento |
| `--confianca` | `0.35` | Confiança mínima por caixa |
| `--iou` | `0.5` | Caixas que se sobrepõem mais que isso viram uma só, qualquer que seja a classe |
| `--area-maxima` | `0.5` | Descarta caixas maiores que essa fração da imagem (o modelo costuma propor uma caixa para a esteira inteira) |
| `--dispositivo` | `cuda` se houver | `cuda` ou `cpu` |
| `--previa` | — | Grava também `previa/<nome>.jpg` com as caixas desenhadas |
| `--sobrescrever` | — | Reanota imagens que já estão na saída |

## Google Colab

Sem GPU no computador, use o notebook [`anotar_colab.ipynb`](anotar_colab.ipynb) ([abrir no Colab](https://colab.research.google.com/github/vdlwang/ecovision-iterativo/blob/main/anotacao/anotar_colab.ipynb)). Ele clona o repositório e roda o próprio `anotar.py`, com as opções acima em formulário; as fotos podem vir do Google Drive ou ser enviadas do computador, e a saída fica no Drive (ou é baixada como `.zip`). Imagens que já têm `.txt` na saída são puladas, então, se o Colab desconectar, basta rodar de novo. O campo `RAMO` escolhe o ramo clonado.

## Saída

Formato de detecção do YOLO, que o Ultralytics treina direto:

```
anotacoes/
├── data.yaml          # names: {0: Clear plastic bottle, ...}, na ordem de classes.yaml
├── images/foto.jpg
├── labels/foto.txt    # uma linha por objeto: id cx cy w h, normalizados de 0 a 1
├── previa/foto.jpg    # só com --previa
└── visualizar.html    # página para conferir as anotações (abaixo)
```

Várias execuções podem gravar no mesmo diretório; o script recusa a saída se o `data.yaml` dela tiver outras classes, porque os ids deixariam de bater. Imagem sem nenhum objeto gera `.txt` vazio (fundo, para o YOLO). Se o EXIF da foto pede rotação (fotos de celular), a imagem é gravada já girada, e as caixas valem para ela.

O `data.yaml` aponta `train` e `val` para a mesma pasta `images`: a divisão deve ser feita por sessão de captura, nunca por imagem (monografia, seção 5.3.5), e fica para quando houver sessões.

O diretório `anotacoes/` está no `.gitignore`: imagens não vão para o repositório (RNF10).

## Visualização

Ao terminar, o `anotar.py` grava `visualizar.html` no diretório de saída e imprime o endereço. A página abre direto no navegador, sem servidor: lista das imagens com a contagem de objetos à esquerda (em laranja, imagem sem `.txt` ou com linhas inválidas), a imagem com as caixas coloridas por classe e a contagem por classe embaixo. As setas `←`/`→` navegam, as caixas e os nomes podem ser escondidos, e `visualizar.html#3` abre a terceira imagem. A página só mostra; corrigir as anotações fica para a interface de revisão (RF12).

A página lê os `.txt` quando é gerada. Depois de editar algum à mão, ou para ver um diretório anotado por outra ferramenta no mesmo formato, gere de novo:

```bash
python anotacao/visualizar.py anotacoes
```

Os `.txt` não guardam a confiança, então ela não aparece na página; para vê-la, use `--previa`.

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

## Testes

```bash
python -m pytest anotacao/tests     # não carregam o modelo; precisam de pytest, pyyaml e pillow
```
