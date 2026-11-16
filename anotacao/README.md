# Anotação assistida

Primeiro passo da anotação assistida prevista na monografia (seção 5.3.4, RF11): `importar.py` grava as imagens de um lote num armazenamento comum, e `anotar.py` propõe caixas para elas com um anotador intercambiável: o [Grounding DINO](https://huggingface.co/IDEA-Research/grounding-dino-tiny) e o [OWLv2](https://huggingface.co/google/owlv2-base-patch16-ensemble), detectores de vocabulário aberto que não dependem do detector em operação, ou o próprio `best.pt` da equipe (`yolo`), o terceiro anotador do voto. As caixas são **propostas** para um revisor humano: ficam no banco da saída (`anotacoes.sqlite`), à parte dos rótulos finais em `labels/`.

## Instalação

Num ambiente separado do backend (o torch é grande):

```bash
pip install -r anotacao/requirements.txt
```

No Linux, o torch do PyPI já vem com CUDA; no Windows, ele é só para CPU, e para usar a GPU é preciso instalar antes o torch com CUDA ([pytorch.org](https://pytorch.org/get-started/locally/)). Roda também sem GPU, só que mais devagar. Na primeira execução, os pesos (~700 MB para o `tiny`) são baixados do Hugging Face para `~/.cache/huggingface`.

## Uso

```bash
python anotacao/importar.py fotos/ -o anotacoes --lote 2026-11-11a   # copia para anotacoes/images
python anotacao/anotar.py -o anotacoes --previa          # anota as pendentes ainda sem proposta
python anotacao/anotar.py 2026-11-11a_foto.jpg -o anotacoes --sobrescrever
python anotacao/votar.py anotacoes                       # voto entre os anotadores
python anotacao/revisar.py anotacoes --abrir             # revisão, a partir do voto
```

Ou, de uma vez, com os anotadores de [`anotadores.yaml`](anotadores.yaml) ([Pipeline](#pipeline)):

```bash
python anotacao/pipeline.py -o anotacoes fotos/ --lote 2026-11-15a   # importa, anota e vota
python anotacao/pipeline.py -o anotacoes                             # retoma o que faltou
```

### Importar

O `importar.py` grava cada imagem uma vez em `images/<lote>_<nome>` e a registra no banco da saída (`anotacoes.sqlite`) como `pendente`, no lote (a importação), com a largura, a altura e o conjunto. Todos os anotadores leem de lá; nenhum copia imagens (`OBJETIVO.md`, seção 6). Importar de novo pula as imagens já importadas.

- **A imagem muda o mínimo**: é copiada byte a byte, a não ser que o EXIF a gire (fotos de celular; ela é gravada já girada, e as caixas valem para ela) ou que passe de `--lado-maximo`. Sem normalizar cor nem recortar: a base de treino tem de parecer com o que a câmera vê na operação.
- **Conjunto por imagem**: cada imagem vai para `treino` ou `teste` pelo hash do nome final (`<lote>_<nome>`), cerca de 1 em cada 10 para o teste, sempre o mesmo para o mesmo nome; `--conjunto` força o de todas as imagens da importação. Depois de gravado no banco, não muda. Sortear por imagem só não vaza cenas entre as bases porque a captura (T4) não grava quadros próximos demais (decisão 7 do `OBJETIVO.md`, revista em 2026-11-15); com o T4, a captura grava o horário de cada quadro, espaçado em pelo menos uma janela Δ, e a importação passa a acusar imagens mais próximas que Δ (pelo horário da captura ou do EXIF) e a pô-las no mesmo conjunto.
- **Região de interesse** (`--regiao X1 Y1 X2 Y2`, de 0 a 1): os anotadores descartam caixas com o **centro** fora dela (a mesa em volta da esteira). A imagem continua inteira.

| Opção | Padrão | |
|---|---|---|
| `-o`, `--saida` | `anotacoes` | Diretório de saída |
| `--lote` | obrigatório | Nome do lote de captura: letras, dígitos, `.` e `-` (o `_` separa o lote do nome da imagem) |
| `--conjunto` | sorteio | `treino` ou `teste`, para todas as imagens da importação |
| `--regiao` | — | Região de interesse do lote, normalizada |
| `--lado-maximo` | — | Reduz imagens com o lado maior acima disso (só para fotos grandes de outra origem; a da esteira fica na resolução nativa) |
| `--link` | — | Link (hardlink, ou simbólico se não der) em vez de cópia, quando a imagem não precisa ser regravada |
| `--classes` | `anotacao/classes.yaml` | Lista de classes, para o `data.yaml` |

### Anotar

O `anotar.py` só anota imagens importadas e `pendente`: sem nomes na linha de comando, as que ainda não têm proposta do anotador (todas as pendentes com `--sobrescrever`). Imagens revisadas ou descartadas nunca são anotadas de novo, porque o registro da revisão cita a proposta que o revisor viu.

| Opção | Padrão | |
|---|---|---|
| `-o`, `--saida` | `anotacoes` | Diretório de saída, já com imagens importadas |
| `--anotador` | `grounding-dino` | Qual anotador propõe as caixas: `grounding-dino`, `owlv2` ou `yolo` (o `best.pt` da equipe, de conjunto fechado) |
| `--classes` | `anotacao/classes.yaml` | Lista de classes |
| `--nome` | o do anotador | Nome com que as propostas são gravadas, para rodar o mesmo anotador com outra configuração na mesma saída, por exemplo outro peso do YOLO: `--anotador yolo --nome yolo-taco-s --modelo yolo_models/taco/yolov8s.pt`. O tipo do anotador fica gravado à parte, na execução |
| `--dispositivo` | `cuda` se houver | `cuda` ou `cpu` |
| `--previa` | — | Grava também `previa/<anotador>/<nome>.jpg` com as caixas desenhadas |
| `--sobrescrever` | — | Anota de novo imagens pendentes que já têm proposta deste anotador |
| `--exportar` | — | Só refaz do banco os arquivos gerados (`data.yaml`, `labels/`, as listas) e sai |

Opções de detecção, comuns a todo detector. A proposta guarda **todas** as caixas a partir de `--piso`, sempre com a classe; `--confianca` e `--confianca-classe` são gravados nela e aplicados por quem lê (o voto e a página), então dá para mudá-los sem rodar o modelo de novo (decisão 16 do `OBJETIVO.md`).

| Opção | Padrão | |
|---|---|---|
| `--modelo` | o do anotador | `grounding-dino`: `IDEA-Research/grounding-dino-tiny`; também `IDEA-Research/grounding-dino-base`, mais preciso e mais lento. `owlv2`: `google/owlv2-base-patch16-ensemble`; também `google/owlv2-large-patch14-ensemble`. `yolo`: `yolo_models/taco/best.pt` (relativo à raiz do repositório), ou outro peso do Ultralytics |
| `--piso` | `0.05` | Confiança mínima gravada. As caixas entre o piso e `--confianca` são as **candidatas** da caixa por clique (cerca de 11 por foto) |
| `--confianca` | `0.2` | A página mostra as caixas a partir dessa confiança. Baixa de propósito: cobre 92% dos objetos e sobram ~2 caixas por imagem para remover (medida no `OBJETIVO.md`, seção 5) |
| `--confianca-classe` | `0.35` | Abaixo dessa, a página mostra a caixa **sem classe**: o revisor tem de dar a classe ou remover a caixa. A classe do anotador fica gravada, só não chega à página. `0` desliga |
| `--iou` | `0.5` | Caixas que se sobrepõem mais que isso viram uma só, qualquer que seja a classe |
| `--area-maxima` | `0.5` | Descarta caixas maiores que essa fração da imagem (o modelo costuma propor uma caixa para a esteira inteira) |
| `--contencao` | `0.9` | Remove a caixa que tem ao menos essa fração dentro de outra maior e mais confiante (partes do objeto, como o topo da lata proposto como tampa, e duplicatas menores, que o NMS não pega). A caixa grande que envolve uma menor mais confiante fica: em geral é o objeto inteiro. Acima de `1` desliga |

Opções de um anotador só:

| Opção | Padrão | |
|---|---|---|
| `--owlv2-frase` | `{}` | `owlv2`: modelo da consulta de cada prompt, com `{}` no lugar dele (ex.: `"a photo of a {}"`). Fica gravada nos `parametros` da proposta |
| `--yolo-lado` | `640` | `yolo`: lado maior da imagem na entrada da rede, múltiplo de 32 (o do treino do `best.pt`). 960 e 1280 não melhoram a cobertura nas fotos de validação |

### Votar

O `votar.py` decide, para cada imagem **pendente** com proposta vigente de todos os anotadores (o trio é o da decisão 17), de onde a revisão parte. **Toda revisão parte de um voto**: imagem não votada não é revisável.

- **Treino**: o voto NooN estrito (`OBJETIVO.md`, seção 3). A imagem é aprovada se todos propõem o mesmo número de caixas e cada caixa casa, com a mesma classe e IoU ≥ 0,5, com uma de cada um dos outros. A aprovada recebe como rótulo as **caixas de consenso** (a mediana de cada coordenada, com a menor das confianças) e entra no `treino.txt`, sem passar pela revisão. A que falha continua `pendente`, com o motivo (`quantidade`, `caixas`, `vazia` ou `classe_fora`), e vai para a revisão com **uma caixa por objeto**: as caixas visíveis dos anotadores agrupadas como na união do teste (abaixo), em que um grupo achado por todos com a mesma classe é **consenso** e qualquer outro é **conflito**, sem classe.
- **Teste**: não há voto de classe (seção 4). O voto grava a **união** das caixas dos anotadores, sem classe: da mais confiante para a menos, as que se sobrepõem (IoU ≥ 0,5, de anotadores diferentes) viram uma só, na mediana. Toda imagem de teste vai para a revisão, que é **sem pré-anotação**: a união fica no banco, para comparar com a revisão, e não vai à página.

```bash
python anotacao/votar.py anotacoes                                  # grounding-dino, owlv2 e yolo
python anotacao/votar.py anotacoes --anotadores grounding-dino yolo --limiares g 0.05
```

- Cada anotador é lido no limiar de leitura gravado na proposta (`confianca`), ou no de `--limiares` (`g` mantém o gravado). Vale a classe do anotador mesmo abaixo de `confianca_classe`: ela só é escondida do revisor.
- Cada caixa do voto guarda de quais caixas das propostas veio. A revisão usa isso para sugerir as classes de um conflito.
- Rodar de novo vota só as imagens novas e as que ganharam proposta nova de algum anotador. `--revotar` vota de novo todas as pendentes (por exemplo, com outros `--limiares`). Cada voto é uma linha nova no banco, com as propostas e os limiares que usou.
- A revisão humana vale mais que o voto: uma aprovada que o revisor salva passa a ter o rótulo dele, e o voto não mexe mais nela.
- **Auditoria cega** (T8): cerca de 5% das aprovadas (`--auditoria`, `0` desliga), sorteadas pelo hash do nome (sempre as mesmas, mesmo votando de novo), vão à fila "a revisar" como se tivessem falhado, para estimar o erro das aprovadas. No banco continuam aprovadas, marcadas em `votos.auditoria` (e `imagens.auditoria`), com o rótulo de consenso em `labels/` e no `treino.txt` até a revisão. Na página e na API do `revisar.py` nada as distingue de uma reprovada: vêm com o voto `falhou`, sem a anotação final, e, por isso, **o motivo da falha não aparece para nenhuma imagem** (só fica no banco e no resumo do `votar.py`). A página estática (`visualizar.html`) mostra os rótulos de `labels/` e não é cega: o revisor usa só a do `revisar.py`. Fica uma pista que só some mudando o que se mede: uma reprovada quase sempre tem alguma caixa em conflito (vermelha), e uma auditada só tem caixas de consenso.

| Opção | Padrão | O que faz |
|---|---|---|
| `--anotadores` | `grounding-dino owlv2 yolo` | Quem vota (ao menos dois); o primeiro dá a ordem das caixas de consenso |
| `--limiares` | gravados | Um limiar de leitura por anotador, ou `g` |
| `--iou` | `0.5` | IoU mínimo para duas caixas casarem |
| `--auditoria` | `0.05` | Fração das aprovadas na auditoria cega; `0` desliga |
| `--revotar` | — | Vota de novo as já votadas com as mesmas propostas |

### Pipeline

O `pipeline.py` encadeia os três passos acima (`OBJETIVO.md`, seção 6, T14): importa um lote (se receber entradas), roda o `anotar.py` com cada anotador de [`anotadores.yaml`](anotadores.yaml), um de cada vez (o modelo do anterior é liberado antes de carregar o próximo), e vota com eles, na ordem do arquivo: voto NooN nas imagens de treino, união sem classe nas de teste (gravada para comparar; a revisão do teste é sem pré-anotação).

- **Retomável**: a unidade de trabalho é (imagem, anotador). Cada proposta é gravada numa transação, o `anotar.py` pula as imagens que já têm proposta do anotador e o voto pula as já votadas com as mesmas propostas. Interrompida (Ctrl+C, queda do Colab), basta rodar o mesmo comando; sem nada a fazer, nenhum modelo é carregado. Sem entradas, anota e vota o que já foi importado, de qualquer lote.
- **Conferência antes de tudo**: o `anotadores.yaml` e as opções de cada anotador passam pelo `anotar.py` antes de importar ou carregar qualquer modelo, para um erro no terceiro não aparecer depois de horas de GPU.
- **Registro**: cada execução grava a versão e os parâmetros do anotador, como no `anotar.py`, e a votação grava a configuração inteira (RNF07).

O `anotadores.yaml` lista os anotadores (`nome`, `tipo` e `opcoes`, as opções do `anotar.py` sem o `--`: as de detecção e as do próprio tipo, como `yolo-lado`) e o `iou` do voto. O do repositório tem o trio da decisão 17. Para comparar outra configuração, copie o arquivo e passe `--config`.

| Opção | Padrão | |
|---|---|---|
| `-o`, `--saida` | `anotacoes` | Diretório de saída |
| `--config` | `anotacao/anotadores.yaml` | Anotadores e voto |
| `--classes` | `anotacao/classes.yaml` | Lista de classes |
| `--dispositivo` | `cuda` se houver | Para todos os anotadores |
| `--previa` | — | Grava também `previa/<anotador>/<nome>.jpg` |
| `--lote`, `--conjunto`, `--regiao`, `--lado-maximo`, `--link` | — | Como no `importar.py`; só com entradas |

## Google Colab

Sem GPU no computador, use o notebook [`anotar_colab.ipynb`](anotar_colab.ipynb) ([abrir no Colab](https://colab.research.google.com/github/vdlwang/ecovision-iterativo/blob/main/anotacao/anotar_colab.ipynb)). Ele clona o repositório, instala o `ultralytics` (para o anotador `yolo`) e roda o próprio `pipeline.py`: importa as fotos como um lote (com o conjunto e a região de interesse em formulário), anota com os anotadores do `anotadores.yaml` (ou de uma cópia editada, em `config`) e vota; depois mostra o resumo do voto e as prévias de cada anotador. As fotos podem vir do Google Drive ou ser enviadas do computador, e a saída fica no Drive (ou é baixada como `.zip`). O banco não é usado direto sobre o Drive montado, onde as travas do SQLite não valem: o notebook trabalha numa cópia em `/content` e a grava de volta no Drive ao fim da pipeline, mesmo se ela parar por erro ou interrupção; se o Colab desconectar antes, o que foi anotado depois da última gravação se perde (a pipeline é retomável, então basta rodar de novo). Não rode dois Colabs sobre a mesma saída. O campo `RAMO` escolhe o ramo clonado.

## Saída

```
anotacoes/
├── anotacoes.sqlite                   # o estado: classes, lotes, imagens, propostas, revisões e votos
├── anotacoes.sqlite.bak               # cópia do banco antes de cada anotar.py
├── images/lote_foto.jpg               # gravada pelo importar.py
├── labels/lote_foto.txt               # gerado do banco: rótulos finais (YOLO) das revisadas e aprovadas
├── treino.txt                         # gerado do banco: treino aprovadas pelo voto ou revisadas; train do data.yaml
├── teste.txt                          # gerado do banco: teste revisadas; val do data.yaml (vazio: não treina)
├── revisadas.txt                      # gerado do banco: as revisadas por humano, de qualquer conjunto
├── data.yaml                          # gerado do banco: names (TACO + Background), train e val
├── previa/grounding-dino/foto.jpg     # só com --previa
└── visualizar.html                    # página para conferir propostas e rótulos (abaixo)
```

O **banco** (SQLite, biblioteca padrão do Python) é a fonte do estado; `labels/`, as listas (`treino.txt`, `teste.txt`, `revisadas.txt`) e `data.yaml` são gerados dele, para o Ultralytics e o Colab, que leem arquivos. Cada operação grava primeiro no banco, numa transação, e depois os arquivos daquela imagem; interrompida entre os dois, o banco vale, e `anotar.py --exportar` (ou a abertura do `revisar.py`) refaz os arquivos. O `importar.py`, o `anotar.py`, o `votar.py` e o `revisar.py` podem rodar ao mesmo tempo sobre a mesma saída: cada gravação é uma transação, e quem chega depois espera. Para inspecionar: `sqlite3 anotacoes/anotacoes.sqlite` ou o DB Browser for SQLite. O esquema está no `saida.py` e no [`PLANO-REVISAO.md`](PLANO-REVISAO.md), seção 6:

| Tabela | O que guarda |
|---|---|
| `classes` | O id YOLO e o nome de cada classe de `nomes` do `classes.yaml`; só aceita acréscimo no fim depois que alguma revisão ou algum voto guarda caixa com classe |
| `lotes` | Região de interesse e data de cada lote (importação); o conjunto (`treino` ou `teste`) é de cada imagem, em `imagens` |
| `imagens` | Nome, tamanho, lote, conjunto, status (`pendente`, `revisada`, `descartada`) e, do voto vigente (T6, T8), `voto`, `motivo` e `auditoria` |
| `execucoes` | Uma por chamada do `anotar.py`: o nome do anotador (o de `--nome`), o tipo, a versão do modelo, os parâmetros (com os limiares de leitura) e o hash das classes |
| `propostas`, `caixas_propostas` | O que cada execução propôs em cada imagem: todas as caixas desde o piso, com a classe pelo nome e a confiança, coordenadas de 0 a 1 |
| `votacoes`, `votos`, `votos_propostas`, `caixas_voto`, `caixas_voto_membros` | Cada rodada do `votar.py` (anotadores e parâmetros) e, por imagem votada, o resultado (`aprovada`, `falhou`, `uniao`), o motivo, se entrou na auditoria cega, as propostas usadas com o limiar de cada uma, as caixas (de consenso no treino, da união sem classe no teste) e de quais caixas das propostas cada uma veio. O resultado do voto vigente é repetido em `imagens.voto`, `imagens.motivo` e `imagens.auditoria` |
| `revisoes`, `caixas_revisao` | Cada sessão de revisão: ação, data, tempo ativo, revisor, o voto de onde partiu e as caixas finais, cada uma com a origem (uma caixa do voto, uma proposta fora dele ou uma candidata) e o desfecho |

As propostas ficam separadas dos rótulos por dois motivos. O Ultralytics trata imagem sem objetos como fundo, então uma imagem não revisada com `.txt` entraria no treino como negativo falso. E, sem a proposta original, não dá para medir quanto o revisor corrigiu cada anotador (RF13). Por isso o `data.yaml` aponta para as listas, e não para `images/`.

**Nada é sobrescrito.** Anotar de novo (`--sobrescrever`) grava uma proposta nova, e a vigente de um anotador numa imagem é a mais recente; as anteriores continuam no banco, e o voto guarda quais versões usou. Cada revisão é uma linha nova, e a vigente é a mais recente. A proposta guarda a classe pelo nome (o anotador pode propor classe fora do `data.yaml`) e as caixas da mais confiante para a menos. Quem lê aplica os limiares de leitura gravados nos parâmetros da execução (`confianca`, `confianca_classe`): a página mostra a partir de `confianca`, esconde a classe abaixo de `confianca_classe` e oferece as de baixo como candidatas. O registro da revisão cita cada caixa pelo índice na lista do voto ou na proposta, que não muda com os limiares. Uma imagem entra como `pendente` ao ser importada, e anotar não muda o status dela. Os rótulos em `labels/` usam o formato de detecção do YOLO (`id cx cy w h`, de 0 a 1), e uma imagem revisada sem objetos tem `.txt` vazio (fundo).

Várias execuções podem gravar no mesmo diretório. Se o `classes.yaml` tiver outras classes, o banco as troca quando nenhuma revisão nem voto guarda caixa com classe (as propostas guardam a classe pelo nome; fundo, descarte e a união do teste não têm ids); depois disso, só aceita classes novas no fim, porque os ids deixariam de bater. Saídas dos formatos anteriores (com `imagens.csv`, só com `labels/`, ou um banco de outra versão do esquema) são recusadas, sem migração: importe de novo numa saída nova. Toda imagem entra pelo `importar.py`, num lote, com o seu conjunto; não há imagem sem lote.

**Treino e teste** são divididos por imagem, no `importar.py` (1 em cada 10 para o teste; o vazamento entre as bases é evitado na captura, decisão 7 do `OBJETIVO.md`, conferida pelo horário de captura a partir do T4). O `treino.txt` recebe as imagens de treino aprovadas pelo voto ou revisadas, e o `teste.txt`, só as de teste revisadas (seção 2 do `OBJETIVO.md`). Uma imagem com rótulo final tem `.txt` em `labels/`: a revisada, com as caixas da revisão, e a aprovada pelo voto que ainda não foi revisada, com as caixas de consenso. O `data.yaml` usa `treino.txt` como `train` e `teste.txt` como `val`: a validação do YOLO é feita nas imagens de teste, anotadas por humanos sem pré-anotação (seção 4 do `OBJETIVO.md`). Enquanto nenhuma imagem de teste foi revisada, o `teste.txt` fica vazio e o Ultralytics não treina, de propósito.

O diretório `anotacoes/` está no `.gitignore`: imagens não vão para o repositório (RNF10).

## Visualização

Ao terminar, o `anotar.py` grava `visualizar.html` no diretório de saída e imprime o endereço. A página abre direto no navegador, sem servidor. À esquerda fica a lista das imagens, com a contagem de objetos e o status. À direita, a imagem com as caixas coloridas por classe e, embaixo, a contagem por classe. O seletor "mostrar" escolhe o que é desenhado:

- **automático** (padrão): a anotação final se a imagem tem `.txt`; senão, as propostas vigentes do primeiro anotador que tiver alguma;
- **anotação final**: só `labels/`;
- **propostas: \<anotador\>**: as propostas de um anotador.

As propostas aparecem tracejadas e com a confiança, e as caixas finais em linha contínua. As setas `←`/`→` navegam, as caixas e os nomes podem ser escondidos, e `visualizar.html#3` abre a terceira imagem. A página só mostra; corrigir fica para a página de revisão (RF12, [`PLANO-REVISAO.md`](PLANO-REVISAO.md)).

A página lê o banco e `labels/` quando é gerada. Depois de anotar ou revisar mais imagens, ou para ver um diretório no formato YOLO gerado por outra ferramenta (só `data.yaml`, `images/` e `labels/`, sem banco), gere de novo:

```bash
python anotacao/visualizar.py anotacoes
```

## Revisão

`revisar.py` serve uma página local de revisão sobre um diretório do `anotar.py`, sem dependência além das do script:

```bash
python anotacao/revisar.py anotacoes --abrir      # http://127.0.0.1:8000/
python anotacao/revisar.py anotacoes --porta 8001
```

A revisão parte do voto (`votar.py`). A fila padrão, **a revisar**, tem as imagens pendentes que falharam no voto, as aprovadas sorteadas para a auditoria cega (sem o revisor saber quais) e as de teste, das mais incertas para as mais seguras: a ordem é pela menor confiança entre as caixas propostas, e as imagens sem nenhuma caixa vêm primeiro, porque são as que mais podem ter objeto não achado. Os outros filtros mostram as **aprovadas** pelo voto, menos as da auditoria (já rotuladas; revisá-las troca o rótulo pelo do revisor), as **sem voto** (só para ver: rode o `votar.py`), as revisadas, as descartadas e todas; a ordem também pode ser por nome. As setas `←`/`→` andam pela fila, e `#<nome da imagem>` no endereço abre aquela imagem.

### Edição

Numa imagem pendente e votada, com "mostrar" em "automático (edição)", a edição começa com as **caixas do voto** no treino, e sem nenhuma no teste:

- **Treino**: uma caixa por objeto. As de **consenso** (todos os anotadores a acharam com a mesma classe) vêm com a classe e a menor confiança. As demais aparecem só como **conflito**, em vermelho: algum anotador não a achou, ou eles discordam da classe. Ao selecionar um conflito, a busca vazia lista as classes que os anotadores propuseram, uma por classe, com quem propôs e a confiança (mesmo abaixo de `confianca_classe`), das propostas por mais anotadores para menos; `1`, `2`, `3` escolhem a sugestão, e escrever busca em todas as classes. Chegar a um conflito pelo `Tab` já abre a busca com as sugestões, como o clique.
- **Teste**: **sem pré-anotação** (seção 4 do `OBJETIVO.md`). A imagem abre sem caixas, e a página não mostra classe, confiança nem quem propôs, nem pelas camadas de propostas. O revisor acrescenta cada objeto pela caixa por clique (`N` e um clique nele) e dá a classe. As candidatas são uma por objeto que os anotadores acharam (a caixa mais confiante do grupo da união) mais as abaixo do limiar de leitura; objeto sem candidata leva ao descarte da imagem (decisão 12).

Caixa do voto intocada aparece tracejada, com a confiança; caixa corrigida ou incluída, em linha contínua. Caixa sem classe aparece em vermelho: a imagem só pode ser salva depois que cada uma recebe classe ou é removida.

| Ação | Mouse | Teclado |
|---|---|---|
| Selecionar caixa | clique (já abre a busca) | `Tab` / `Shift+Tab`, em ordem de leitura |
| Trocar a classe | escrever no campo de busca e clicar na opção | com a caixa selecionada, escrever (a primeira letra já abre a busca); `↑`/`↓` e `Enter` escolhem |
| Escolher uma sugestão de um conflito | clicar na opção da busca | `1`–`3`, com a caixa selecionada (a busca aberta e vazia, ou fechada) |
| Remover caixa | "Remover caixa" | `Del`, também com a busca aberta; `Backspace` com a busca vazia ou fechada |
| Desfazer a seleção | clique fora das caixas | `Esc` |
| Desfazer e refazer | — | `Ctrl+Z`; `Ctrl+Shift+Z` ou `Ctrl+Y` (`Cmd` no Mac). Valem para trocar classe, remover e adicionar caixa, na imagem atual; na busca com texto, ficam com o campo |
| Nova caixa por clique | "Nova caixa" e um clique no objeto | `N` (sem caixa selecionada), clique no objeto, `Tab`/`Shift+Tab` ou a roda do mouse trocam a candidata, `Enter` confirma, `Esc` cancela |
| Salvar e ir para a próxima | "Salvar e próxima" | `Enter`, que pede confirmação (`Enter` confirma, `Esc` cancela); `Ctrl+S` (`Cmd+S` no Mac) salva direto, também com a busca aberta |
| Descartar a imagem (inútil para treino) | "Descartar imagem" | `D` sem caixa selecionada (com uma selecionada, o `d` vai para a busca); sempre pede confirmação |

O `Tab` passa por todas as caixas da edição, na ordem de leitura pelos centros: linhas de cima para baixo e, em cada linha, da esquerda para a direita. Uma caixa entra na linha atual se o centro dela cai na faixa vertical da primeira caixa da linha, a mais alta. O campo de busca mostra a posição da caixa nessa ordem ("caixa 2 de 7").

A busca oferece qualquer classe do `data.yaml` e mostra até 9 opções. Não diferencia maiúsculas nem acentos e casa, nesta ordem: o início do nome, o início de uma palavra ("can" → `Drink can`), as iniciais ("cpb" → `Clear plastic bottle`), um trecho qualquer e o material, em português ou inglês ("vidro" → as classes de vidro do anotador; só elas têm material). Nos empates, vêm antes as classes usadas há pouco e as do anotador. Com o campo vazio, a lista mostra essas mesmas, ou as sugestões dos anotadores numa caixa em conflito. Não há mais atalhos numéricos para as classes do `classes.yaml`: os números são das sugestões. Na busca, `Esc` fecha sem trocar e `Tab` passa para a caixa seguinte.

A confirmação do `Enter` resume o que vai ser gravado: as classes das caixas, quantas foram corrigidas, adicionadas e removidas, e o aviso de fundo quando não sobra nenhuma caixa. Salvar pelo botão ou por `Ctrl+S` não pede confirmação.

Salvar sem mudar nada aceita as caixas do voto como estão. Salvar uma imagem sem caixas a grava como fundo (`.txt` vazio). Salvar grava a revisão no banco, gera `labels/<nome>.txt` e marca a imagem como `revisada`; descartar grava a revisão, apaga o `.txt`, se houver, e a marca como `descartada`. Nos dois casos, a imagem sai da fila. Trocar de imagem com alterações não salvas pede confirmação.

**Nova caixa por clique.** Para um objeto sem caixa: `N`, depois um clique no objeto. A página mostra, tracejada em branco, a candidata mais confiante que contém o ponto, entre as caixas abaixo do limiar do voto (de `--piso` para cima) de **todos** os anotadores; das quase iguais entre si (IoU ≥ 0,9) fica só a mais confiante, e as quase iguais a uma caixa já presente ficam de fora. `Tab` ou a roda passam às seguintes; `Enter` confirma, e a caixa nasce sem classe, com a busca já aberta. Se nenhuma candidata servir, clique em outra parte do objeto. No teste, a confiança das candidatas não aparece.

Desfazer tudo volta às caixas do voto como chegaram, e a imagem deixa de contar como alterada. Ainda não dá para desenhar à mão, mover ou redimensionar caixas: um objeto que nenhuma candidata cobre leva ao descarte da imagem (decisão 12 do `PLANO-REVISAO.md`). Também não dá para reabrir uma imagem revisada ou descartada (fase 5): as outras camadas e filas são só para ver.

Cada revisão é uma linha nova no banco (RF13); a API devolve a vigente assim:

```json
{"imagem": "foto.jpg", "acao": "salvar", "data": "2026-11-15T00:13:30-03:00",
 "tempo_ativo_s": 6.0, "revisor": null, "voto_id": 42,
 "caixas": [{"id": 2, "caixa": [x1, y1, x2, y2], "origem": "voto", "indice": 0,
             "anotador": null, "desfecho": "classe_corrigida"},
            {"id": 5, "caixa": [x1, y1, x2, y2], "origem": "proposta", "indice": 3,
             "anotador": "owlv2", "desfecho": "adicionada"}],
 "removidas": [1]}
```

O servidor confere a origem de cada caixa: uma caixa do voto (`origem: "voto"`, `indice` na lista do voto), ou uma caixa de um anotador usado pelo voto, com `anotador` e o `indice` na proposta: `"candidata"`, abaixo do limiar de leitura, ou `"proposta"`, visível (no treino a página só usa as candidatas; no teste, também a caixa visível que representa cada objeto); as coordenadas têm de ser as da origem. Numa imagem de teste, caixa com origem `"voto"` é recusada: a revisão é sem pré-anotação. O desfecho é calculado por ele: `aceita` ou `classe_corrigida` frente à classe da caixa do voto, `classe_atribuida` quando a caixa do voto não tinha classe (conflito ou teste), e `adicionada` para as que vêm de uma candidata. `removidas` lista as caixas do voto apagadas. O tempo ativo só conta com a aba visível e em foco, e pausa depois de 60 s sem interação.

### Servidor e API

O servidor escuta só em `127.0.0.1` e lê o banco a cada pedido, então propostas gravadas pelo `anotar.py` com a página aberta aparecem ao recarregar. Ao subir, refaz os arquivos gerados a partir do banco. Gravações aceitam só o `Host` local, para que um site aberto no navegador não consiga gravar pela porta (DNS rebinding). A API, em JSON, é a mesma que a página usa:

| Rota | Resposta |
|---|---|
| `GET /api/classes` | `[{id, nome, material}]` |
| `GET /api/imagens?status=a_revisar&ordem=incerteza` | `{imagens: [{nome, status, situacao, voto, motivo, anotadores, n_caixas, confianca_min, tem_final}], anotadores, contagem}`; `status` é a situação: `a_revisar`, `aprovada`, `sem_voto`, `revisada`, `descartada` ou `todas`. Nas de teste pendentes, sem anotadores nem confiança. `motivo` vem sempre nulo, e a aprovada da auditoria vem como `voto: "falhou"`, `situacao: "a_revisar"` e `tem_final: false` (auditoria cega) |
| `GET /api/imagens/<nome>` | `{nome, status, situacao, conjunto, largura, altura, final, propostas: {anotador: [...]}, voto, invalidas, revisao}`; `voto` (nulo sem voto): `{id, resultado, motivo, conjunto, caixas: [{indice, id, nome, conf, caixa, anotadores, sugestoes: [{id, nome, anotadores: [{anotador, conf}]}]}], candidatas: [{anotador, indice, origem, conf, caixa}]}`; caixa de treino com `id` nulo é conflito, com as `sugestoes`. No teste pendente, `propostas` e `voto.caixas` vêm vazios, e as candidatas incluem uma caixa visível por objeto da união (`origem: "proposta"`) |
| `GET /api/metricas?auditoria=1` | As medidas do `metricas.py` (`medir()`); sem `auditoria=1`, cegas: sem o bloco `auditoria`, com as auditadas no grupo `falhou`, e o voto só com `treino_votadas`, `aprovadas` (fora da auditoria), `a_revisar`, `teste_unidas` e `sem_voto` |
| `PUT /api/imagens/<nome>` | Recebe `{acao: "salvar" \| "descartar", voto_id, tempo_ativo_s, caixas: [{id, caixa, origem, indice, anotador}]}` e devolve o mesmo que o `GET`. 400 para pedido inválido (nada é gravado); 409 se a imagem não está pendente, não foi votada, ou se `voto_id` não é mais o voto vigente (a imagem foi votada de novo depois que a página abriu) |
| `GET /images/<nome>` | A imagem |

As caixas vão como `{id, nome, conf, caixa: [x1, y1, x2, y2]}`, normalizadas de 0 a 1, com `conf` nula na anotação final e `id` nulo para classe fora do `data.yaml`. Só imagens registradas no banco são servidas. Conferir o status, gravar a revisão e mudar o status são uma transação só; o `.txt` vem depois, e, se faltar, a próxima abertura do servidor o refaz.

## Novo anotador

Um **detector** é uma subclasse de `Detector` em `anotar.py`, registrada no dicionário `ANOTADORES`. Ela define `nome` (o valor de `--anotador`, e o nome das propostas sem `--nome`) e `MODELO_PADRAO`, e implementa só:

- `carregar()`: carrega o modelo `self.versao` em `self.dispositivo` (se `None`, o detector escolhe);
- `pontuar(imagem)`: recebe a imagem PIL em RGB e devolve `(pontuacoes, caixas)`, a pontuação de cada classe (na ordem de `classes.yaml`) em cada caixa bruta, como lista de listas ou tensor, e as caixas `(x1, y1, x2, y2)` normalizadas de 0 a 1.

A base faz o resto, igual para todos: escolhe a classe de cada caixa (com a de reserva), aplica o piso, a área máxima, o NMS sem classe e a contenção, e grava os limiares de leitura em `parametros`. Opções próprias do detector entram em `opcoes(parser)`; as de detecção são comuns. Argumentos próprios do construtor vêm das opções por `argumentos(args)`. O que cada um faz com o `prompt` das classes é dele (o `Yolo` o ignora e casa as classes pelo nome com as do modelo). `GroundingDino`, `Owlv2` e `Yolo` são os exemplos. Para a pipeline usá-lo, acrescente-o ao `anotadores.yaml` com `tipo` igual ao `nome` da classe; as opções próprias dele entram em `opcoes` se ficarem num grupo de argumentos com esse mesmo título.

Um anotador que não detecta (por exemplo, um que só reclassifica as caixas de outro) pode implementar a interface direto: `nome`, `opcoes(parser)`, `criar(classes, args)` e, na instância, `versao`, `parametros` e `anotar(imagem) -> [(id da classe, confiança, caixa normalizada)]`.

## Classes

`classes.yaml` tem duas listas (nível 2 da taxonomia):

- `nomes`: as classes dos rótulos. O índice é o id nos `.txt`, e o `data.yaml` de cada saída é gerado dela. São as 60 classes TACO e `Background`, na ordem de `legado/database/tcc-*/YOLO_dataset/data.yaml` e do `yolo_models/taco/best.pt`, para que as anotações sirvam direto ao fine-tuning dele. Para não invalidar anotações já feitas, só acrescente no fim.
- `classes`: o que o anotador automático procura, um subconjunto de `nomes`, cada uma com o `nome`, o `prompt` em inglês enviado ao modelo (um texto ou uma lista deles) e o `material` (nível 1). A ordem dela não muda os ids. A lista inicial são as seis classes TACO das fotos da equipe, mais `Glass jar` e `Glass cup`: o vidro é dividido em garrafas, potes e copos (decisão 8 do [`OBJETIVO.md`](../OBJETIVO.md)).

Na revisão, qualquer classe de `nomes` pode ser escolhida, mesmo as que o anotador não procura.

Uma classe de `classes` com `reserva: true` só vence numa caixa quando nenhuma das outras chega ao limiar de confiança. Serve para uma classe genérica (por exemplo, `Unlabeled litter` com o prompt "object") dar caixa aos objetos que as outras não reconhecem, sem tirar delas os que reconhecem. Nenhuma classe a usa por enquanto: a frase a mais no prompt muda a pontuação das outras (medição na seção 5 do [`OBJETIVO.md`](../OBJETIVO.md)).

O prompt é o que mais muda o resultado. Prefira descrições visuais curtas ("cardboard box" em vez de "corrugated carton"), e use `--previa` para conferir. Uma classe pode ter **vários prompts** (`prompt: [glass jar, glass food jar]`): a confiança dela é a maior entre eles. Serve para objetos diferentes na mesma classe (copo, taça e tigela em `Glass cup`), mas um prompt a mais também atrai objetos de outras classes; meça com o `avaliar.py` (seção 5 do `OBJETIVO.md`).

Como cada caixa recebe uma classe: o Grounding DINO dá uma pontuação por token do texto, e a confiança de uma classe é a maior entre os tokens do seu prompt; o OWLv2 dá uma pontuação por consulta, uma consulta por prompt (ou pela frase de `--owlv2-frase`), em cada fragmento da imagem, e a classe fica com a maior das suas; o YOLO dá a pontuação de cada uma das suas 61 classes em cada âncora, e só as de `classes.yaml` contam. Nos três, vence a classe de maior confiança.

## Avaliação

`avaliar.py` mede as **propostas gravadas** de um anotador contra as fotos rotuladas pela equipe (por padrão, as 88 imagens das quatro validações de `legado/database`, 375 caixas nas classes de `classes.yaml`). Ele não roda modelo: a validação é importada e anotada como qualquer lote, uma vez por anotador, e a avaliação leva menos de um segundo, quantas vezes for preciso.

```bash
for c in 0CF 0SF 45CF 45SF; do
  python anotacao/importar.py legado/database/tcc-$c/YOLO_dataset/validation/images \
    -o validacao --lote tcc-$c --link
done
python anotacao/anotar.py -o validacao --anotador grounding-dino          # GPU, ~2 min
python anotacao/avaliar.py validacao --anotador grounding-dino --json gdino.json
```

Cada imagem é casada com o rótulo da equipe pelo nome original (sem o prefixo `<lote>_`); um nome em duas pastas de rótulos é recusado. Imagens sem rótulo são ignoradas e contadas. As medidas (IoU ≥ 0,5 como acerto de posição):

| Medida | Para quê |
|---|---|
| **Cobertura sem classe**, por limiar de leitura: objetos com alguma caixa, imagens completas, caixas e sobra por imagem, e classe e material certos entre as caixas que cobrem um objeto | Escolher `--confianca` |
| **Classificação** no limiar de leitura gravado na proposta: matriz de confusão, com "sem caixa visível" e "outra" (classe fora de `classes.yaml`) | Ver quais classes se trocam |
| **Classe por faixa de confiança**, sobre todas as caixas gravadas | Escolher `--confianca-classe` |
| **Detecção** com classe, por limiar: precisão e recall | Comparar com a linha de base |
| **Caixa por clique**: nos objetos sem caixa visível, se a 1ª (ou uma das 3 primeiras) candidata no centro do objeto tem IoU ≥ 0,75 | Escolher `--piso` |

Com `--comparar OUTRO`, mede também o **erro conjunto de classe** dos dois anotadores, sobre os objetos que ambos cobrem: quantas vezes os dois erram, quantas concordam na mesma classe errada (o que o voto aprovaria) e quais confusões repetem, contra o esperado se os erros fossem independentes dada a classe verdadeira. Serve para escolher o trio do voto: anotadores que erram juntos valem menos que um mais fraco que erra diferente (`OBJETIVO.md`, seção 5). Cada um é lido no limiar gravado na sua proposta, ou nos de `--limiares-par A B`.

```bash
python anotacao/avaliar.py validacao --anotador owlv2 --comparar grounding-dino --limiares-par 0.10 0.20
```

Com `--voto A B C`, mede só o **voto** (seção 3 do `OBJETIVO.md`) entre os anotadores, cada um no limiar gravado na sua proposta ou nos de `--limiares-voto` (`g` mantém o gravado). Por imagem, o NooN estrito: a imagem passa se todos propõem o mesmo número de caixas e cada caixa casa, com a mesma classe e IoU ≥ 0,5, com uma de cada um dos outros. Mostra a taxa de aprovação, os motivos de reprovação e, nas aprovadas, quantas estão corretas por inteiro (e só pelo material). Por caixa, sem exigir a imagem inteira: quantas caixas têm consenso, quantas estão certas, e quantos objetos ganham caixa de consenso.

```bash
python anotacao/avaliar.py validacao --voto grounding-dino owlv2 yolo --limiares-voto 0.20 0.10 0.05
```

Os limiares abaixo do `piso` das propostas não são medidos (faltariam caixas ali). `--json` grava todas as medidas, para registrar a medição e comparar anotadores. Os números ficam no `OBJETIVO.md` (seção 5).

Os rótulos da equipe usam nomes TACO; entram só as classes que estão em `classes.yaml`, casadas pelo nome, e os polígonos viram a caixa que os contém. Antes disso, o `avaliar.py` aplica [`correcoes_rotulos.yaml`](correcoes_rotulos.yaml): a equipe rotulou todo vidro como `Glass bottle`, e as 97 caixas são, na verdade, potes, copos, taças, tigelas e 3 latas. O arquivo indica a linha de cada `.txt` e confere a classe original; `legado/` não é editado. `--sem-correcoes` usa os rótulos como estão, e `--correcoes` aponta para outro arquivo. As quatro validações são as mesmas cenas fotografadas de jeitos diferentes, então somá-las não equivale a quatro vezes mais dados; serve para comparar anotadores, que não treinaram nelas.

## Métricas

O `metricas.py` (RF13, T10) lê o banco da saída e mede o uso da anotação, sem rodar modelo nem mudar nada. As mesmas medidas estão na aba **Métricas** da página de revisão (abaixo):

```bash
python anotacao/metricas.py anotacoes                      # tabelas no terminal
python anotacao/metricas.py anotacoes --json metricas.json # e todas as medidas em JSON
```

| Bloco | O que mede |
|---|---|
| Voto | Imagens de treino votadas, aprovadas (e quantas na auditoria cega) e reprovadas por motivo; de teste unidas; pendentes sem voto |
| Auditoria | Das aprovadas sorteadas (T8) já revistas, a fração **correta por inteiro** (o revisor aceitou todas as caixas de consenso, sem trocar classe, remover nem acrescentar; descartar conta como erro), com o intervalo de Wilson de 95% (a amostra é pequena: 5% das aprovadas), e o destino de cada caixa de consenso |
| Correções | O desfecho de cada caixa da revisão vigente (aceita, classe corrigida, classe atribuída, adicionada de uma proposta ou candidata), as caixas do voto removidas e as descartadas, por grupo: `falhou`, `auditoria`, `aprovada` (revista pelo filtro) e `teste` |
| Tempo | Tempo ativo de revisão por imagem (mediana e média) e por objeto (soma dos tempos sobre a soma das caixas salvas), por grupo |
| Avisos | Estados que o banco não deveria ter (status sem a revisão que o explica, conjunto e resultado do voto que não batem) e limites da leitura (sem imagem de teste revisada, menos de 20 auditadas revistas, revisão com tempo zero) |
| Anotadores | Precisão e recall de cada anotador frente à revisão salva, das caixas visíveis da proposta que o voto usou (casamento guloso, IoU ≥ `--iou`, padrão 0,5), sem e com a classe, separados em treino e teste |

Cuidados ao ler:
- **Treino é enviesado**: a revisão parte das caixas do voto e herda delas (viés de automação), então a precisão dos anotadores no treino sai otimista. O **teste**, revisado sem pré-anotação, é a referência, mas as caixas dele ainda vêm das candidatas dos anotadores (sem desenho à mão, decisão 12): um objeto que nenhum anotador cobre não entra, e o recall sai otimista também.
- **Tempo por clique**: o tempo do teste é o da revisão por clique, não o da anotação manual.
- **Aba Métricas** (`revisar.py`): a mesma medida, **cega por padrão**, porque quem a abre é o revisor. As auditadas contam com as reprovadas, o bloco da auditoria não aparece, e o voto mostra só o que a fila mostra (aprovadas fora da auditoria e a revisar, sem a taxa nem os motivos); senão, o revisor veria o contador da auditoria subir ao salvar uma auditada, ou deduziria quantas são. A opção "mostrar a auditoria" traz tudo, quebrando a cegueira; o `metricas.py` no terminal mostra sempre tudo. Clicar numa imagem da fila volta à revisão, e os atalhos de revisão não valem na aba.
- Só conta a revisão vigente de cada imagem, e só a revisão salva entra na precisão e no recall (descartada não tem caixas finais). No teste, nenhuma caixa conta como removida: a união do voto não vai à página.

## Próximos passos

O plano do framework de anotação e da página de revisão (escopo atual) está em [`PLANO-REVISAO.md`](PLANO-REVISAO.md); o sistema completo, com voto entre anotadores e bases de treino e teste, em [`OBJETIVO.md`](../OBJETIVO.md).

## Testes

```bash
python -m pytest anotacao/tests     # não carregam o modelo; precisam de pytest, pyyaml e pillow
```
