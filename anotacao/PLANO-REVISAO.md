# Plano — framework de anotação e página de revisão

Escopo atual do projeto (tarefa T1 do [`OBJETIVO.md`](../OBJETIVO.md), que descreve o sistema completo: fluxo, voto 3oo3, bases de treino e teste). Requisitos da monografia (`docs/ecovision-iterativo-prelim.pdf`): RF11 (pré-anotação), RF12 (revisar), RF13 (registro de tempo e correções), RNF08 (usabilidade).

**Objetivo**: um framework genérico em que qualquer anotador (detector de vocabulário aberto, classificador, o próprio YOLO) grava propostas num formato comum, e uma página local para ver essas propostas, corrigi-las e editá-las até virarem anotações finais no formato YOLO. Voto entre anotadores, sorteio treino/teste, auditoria e métricas ficam para as tarefas seguintes do `OBJETIVO.md`, mas o formato já deixa espaço para eles.

**Status**: `[ ]` pendente · `[x]` feito (com hash) · `[~]` parcial

**Ponto de partida**:
- `anotar.py` (`e502a35`): o Grounding DINO propõe caixas e as grava direto em `labels/`, no formato YOLO. Desde a fase 1 (`8a0253d`), grava propostas em `propostas/<anotador>/` e o status em `imagens.csv`; desde a fase 3b (2026-11-13), tudo no banco SQLite (seção 6).
- `visualizar.py` (`3084516`): página estática (`file://`, só leitura) com as caixas de `labels/`; desde a fase 1, também as propostas.
- `avaliar.py` (`b70ac8a`): mede um anotador contra os rótulos da equipe em `legado/database`.

A ideia é separar o que o anotador propõe do que o revisor aprova, e evoluir a página para uma de revisão, servida por um servidor Python local.

---

## 1. Propostas separadas das anotações finais

Formato das fases 1 a 3, guardado aqui como histórico. **Desde a fase 3b (2026-11-13)**, `imagens.csv`, `propostas/`, `revisoes/` e `lotes.yaml` estão num banco SQLite (seção 6), e `labels/`, `revisadas.txt` e `data.yaml` são gerados dele; a separação entre proposta e rótulo final continua a mesma. O formato em vigor está no `anotacao/README.md` ("Saída").

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
- **Compatibilidade**: `anotar.py --aceitar` copiava as propostas de um anotador para `labels/` e marcava a imagem como `revisada` (proposta direto como rótulo). Saiu em 2026-11-15: toda revisão parte de um voto (T7).

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
| Trocar a classe | clique na caixa abre a busca por nome (feito, 2026-11-10) | com a caixa selecionada, escrever o nome; `1`–`9` para as classes do anotador |
| Remover caixa | botão | `Del` |
| Caixa nova por clique (feito, 2026-11-11) | clique no objeto: a candidata mais confiante que contém o ponto | `N`, clique; `Tab` ou a roda trocam a candidata; `Enter` confirma |
| Desenhar caixa nova | arrastar numa área vazia | `N` e depois arrastar |
| Ajustar ou mover caixa | alças nos cantos | — |
| Desfazer | — | `Ctrl+Z`; refazer com `Ctrl+Shift+Z` ou `Ctrl+Y` (feito, 2026-11-11) |
| Salvar e ir para a próxima | botão | `Enter`, com janela de confirmação; `Ctrl+S` direto (2026-11-10) |
| Descartar a imagem (inútil para treino) | botão | `D` sem caixa selecionada, com confirmação |

Caixa proposta aparece tracejada e com a confiança; depois de tocada pelo revisor, fica contínua. A fila mostra só as `pendente` por padrão, com filtro por status e ordem por confiança, para começar pelas incertas (RF10). Com mais de um anotador, a página mostra as propostas de um por vez (seletor) ou todas, coloridas por anotador; a vista de concordância do voto é a tarefa T7 do `OBJETIVO.md`. Uma imagem `revisada` pode ser reaberta e editada de novo.

## 5. Registro da revisão (RF13)

O registro da revisão (até a fase 3, `revisoes/<nome>.json`; desde a 3b, as tabelas `revisoes` e `caixas_revisao`) guarda:

- **Tempo ativo**: o cronômetro pausa quando a aba perde o foco ou depois de 60 s sem interação.
- **Desfecho de cada caixa**: `aceita`, `classe_corrigida`, `classe_atribuida` (a classe da proposta estava escondida do revisor, abaixo de `confianca_classe`; 2026-11-11) ou `adicionada` (com `origem`: `candidata`, e `desenho` na fase 4); as propostas que sumiram vão em `removidas`. `caixa_ajustada` fica para a fase 4 (ver abaixo).
- **Versões** do anotador de base e das classes que geraram as propostas.
- **Revisor**: campo já previsto, mesmo com um revisor só (ver decisão 3).
- **Todas as sessões** (desde a fase 3b, 2026-11-13): cada revisão é uma linha nova, e a vigente é a mais recente. Até a fase 3, só a última ficava (o arquivo era sobrescrito, decisão de 2026-11-09).

O servidor calcula os desfechos comparando cada caixa com a proposta de origem, que a página indica pelo índice. Enquanto as caixas não se movem, ele recusa uma caixa que diz vir de uma proposta mas tem outras coordenadas, para que o registro nunca chame de `aceita` uma caixa alterada.

**Para depois** (anotado em 2026-11-09, não implementado):
- **Limiar de `caixa_ajustada`** (fase 4): IoU com a proposta abaixo de um limiar (proposta inicial: 0,9). Uma caixa pode ter dois desfechos (`classe_corrigida` e `caixa_ajustada`), então o campo vira lista.
- **Histórico de sessões**: hoje a revisão de uma imagem reaberta (fase 5) sobrescreve a anterior. Para medir o anotador, vale a primeira; se as métricas (T10) precisarem, o registro vira uma lista de sessões.

O registro é gravado desde a primeira versão da edição, mesmo sem `metricas.py` (tarefa T10 do `OBJETIVO.md`): sem ele, o tempo das primeiras revisões se perde.

## 6. Armazenamento em SQLite (planejado em 2026-11-11)

Substitui `imagens.csv`, `propostas/` e `revisoes/` (seções 1 e 5) por um banco SQLite, `<saida>/anotacoes.sqlite`. As imagens e o que o Ultralytics lê continuam como arquivos.

**Por quê**:
- **Escrita concorrente**: o `anotar.py` e o `revisar.py` reescrevem o mesmo `imagens.csv` inteiro; rodando juntos, um apaga a alteração do outro. No SQLite, cada gravação é uma transação.
- **Propostas sobrescritas**: o `--sobrescrever` troca a proposta de uma imagem já revisada, e o registro da revisão, que aponta para as caixas pelo índice, deixa de corresponder a elas. No banco, anotar de novo cria uma nova versão da proposta, e a revisão guarda qual versão viu.
- **Histórico de sessões** (seção 5, "para depois"): uma tabela de revisões guarda todas as sessões, sem mudar o formato quando a fase 5 reabrir imagens.
- **Consultas**: a fila por incerteza (RF10), o voto (T6) e as métricas (T10) cruzam propostas de vários anotadores com as revisões. Com arquivos, cada consulta lê milhares de JSONs.
- **Momento**: a saída atual foi apagada (2026-11-11), então não há dado a migrar; e a fase 4 mudaria o formato do registro (`caixa_ajustada`, desfecho em lista). Feito antes dela, o formato muda uma vez só.

**Sem dependência nova**: `sqlite3` é da biblioteca padrão. Nada de ORM; SQL direto, concentrado no `saida.py`.

```
anotacoes/
├── images/              # as imagens, como hoje
├── anotacoes.sqlite     # fonte do estado: imagens, propostas, revisões
├── labels/<nome>.txt    # gerado do banco (caixas da última revisão salva)
├── revisadas.txt        # gerado do banco
├── data.yaml            # gerado do banco (tabela classes)
└── previa/              # opcional, como hoje
```

### Esquema

| Tabela | Colunas | Observações |
|---|---|---|
| `classes` | `id` (PK, o id YOLO), `nome` (único) | Espaço de ids do `data.yaml`, carregado de `nomes` no `classes.yaml`. Só aceita acréscimo no fim (decisão 2, RF14); um `classes.yaml` que reordena ou remove é recusado. Substitui a conferência do `data.yaml` no `preparar_saida` |
| `imagens` | `id`, `nome` (único), `stem` (único), `largura`, `altura`, `status` (`pendente`, `revisada`, `descartada`), `criada_em` | `stem` único mantém a recusa de nomes que colidem sem extensão. O sistema completo acrescenta `lote`, `conjunto`, `voto`, `motivo` (`OBJETIVO.md`, seção 2) com `ALTER TABLE` |
| `execucoes` | `id`, `anotador`, `versao`, `parametros` (JSON), `classes_hash`, `data` | Uma por rodada do `anotar.py`. Hoje esses campos se repetem em cada proposta |
| `propostas` | `id`, `imagem_id`, `execucao_id`, `data` | Nunca apagada nem alterada. A proposta atual de um anotador numa imagem é a de maior `id` |
| `caixas_propostas` | `proposta_id`, `indice`, `classe` (nome), `confianca`, `x1`, `y1`, `x2`, `y2` | PK (`proposta_id`, `indice`). Classe pelo nome, como hoje: o anotador pode propor classe fora do `data.yaml`. Coordenadas normalizadas (hoje são pixels no JSON) |
| `revisoes` | `id`, `imagem_id`, `proposta_id` (base, pode ser nula), `acao` (`salvar`, `descartar`), `data`, `tempo_ativo_s`, `revisor` | Uma linha por sessão; nenhuma é sobrescrita. A vigente é a de maior `id` |
| `caixas_revisao` | `revisao_id`, `indice`, `classe_id` (FK `classes`), `x1`..`y2`, `proposta_indice` (nulo se adicionada), `classe_corrigida`, `caixa_ajustada` | Os desfechos viram colunas booleanas, e uma caixa pode ter os dois (seção 5). `aceita` = nenhum dos dois com proposta; `adicionada` = sem proposta; `classe_atribuida` = a classe da proposta estava escondida (confiança abaixo de `confianca_classe` da execução). As removidas não são gravadas: são as caixas da proposta base que nenhuma caixa da revisão cita |

- Versão do esquema em `PRAGMA user_version`; o `saida.py` recusa um banco de versão desconhecida e aplica as migrações conhecidas na abertura.
- `PRAGMA foreign_keys = ON` e `CHECK` nos status, nas ações e em `0 <= x1 < x2 <= 1`, para que um erro de código não grave estado inválido.
- `journal_mode = WAL` e `busy_timeout` de alguns segundos: o servidor lê enquanto o `anotar.py` grava.

### Arquivos gerados

`labels/`, `revisadas.txt` e `data.yaml` passam a ser saídas, regeneradas do banco:

- Cada operação grava primeiro no banco (uma transação) e depois os arquivos daquela imagem, com a gravação atômica de hoje. Interrompida entre os dois, o banco vale; `anotar.py --exportar` (ou a abertura do `revisar.py`) regenera todos os arquivos a partir dele.
- `labels/<stem>.txt` existe só para imagem `revisada`, com as caixas da última revisão `salvar`; fundo continua sendo `.txt` vazio. Descartar apaga o `.txt`.
- O Ultralytics e o Colab continuam lendo arquivos; ninguém precisa abrir o banco para treinar.

### O que muda no código

- **`saida.py`**: as funções de hoje mantêm o papel e trocam a implementação: `ler_estado`/`gravar_estado`/`registrar_imagem` → consultas a `imagens`; `gravar_proposta`/`ler_proposta`/`anotadores` → `execucoes`, `propostas`, `caixas_propostas`; `revisar`/`ler_revisao` → `revisoes`, `caixas_revisao`; `aceitar` grava uma revisão `salvar` sem tempo, com `revisor = "aceitar"`, para que o registro mostre que ninguém olhou. Novas: `abrir(saida)` (conexão com os pragmas e a migração) e `exportar(saida, nomes=None)`.
- **`anotar.py`**: `--sobrescrever` deixa de sobrescrever: grava uma proposta nova (sem a opção, imagem já anotada por aquele anotador continua sendo recusada). Uma imagem já `revisada` ou `descartada` mantém o status; a proposta nova só aparece se ela for reaberta (fase 5). Uma execução por rodada.
- **`revisar.py`**: uma conexão por pedido (o `sqlite3` não compartilha conexão entre threads), com `BEGIN IMMEDIATE` no PUT, para que conferir o status e gravar sejam uma operação só. A fila por incerteza vira uma consulta. A página e a API não mudam, exceto `proposta_id` no detalhe e no PUT, para o servidor saber qual versão foi revisada.
- **`visualizar.py`**: lê pelo `saida.py`, como hoje; a página estática não muda.
- **Colab**: SQLite sobre o Google Drive montado (FUSE) não garante as travas e pode corromper o banco. O notebook copia o banco para `/content` no início e de volta ao Drive no fim (API `backup` do `sqlite3`), e avisa que dois Colabs na mesma pasta não podem rodar juntos.
- **Formato antigo**: `imagens.csv` sem `anotacoes.sqlite` é recusado com uma mensagem, como já acontece com o formato anterior à fase 1. Sem importador: não há dado a preservar.

### Custos e riscos

- O estado deixa de ser legível e comparável em texto. Mitigações: `sqlite3 anotacoes.sqlite` ou o DB Browser for SQLite para inspecionar, e os arquivos gerados continuam em texto.
- Um arquivo binário só: um banco corrompido perde tudo. Cópia de segurança antes de cada `anotar.py` (`anotacoes.sqlite.bak`, via `backup`), barata para o tamanho esperado (milhares de imagens, poucos MB).
- Esforço estimado: ~1 a 1,5 dia, a maior parte reescrevendo os testes do `saida.py` e do `revisar.py` para o banco.

### Ajustes antes de implementar (2026-11-13)

Revisto antes do T6 (`votar.py`), que seria o terceiro escritor do `imagens.csv`, e **implementado no mesmo dia** (ver "Feito" abaixo). `anotacao/anotacoes/` foi recriada do zero, sem importador.

**Esquema, além da tabela acima:**
- `imagens` já nasce com `lote` (FK `lotes`, pode ser nulo), `voto` (`aprovada`, `falhou` ou nulo) e `motivo`; o `conjunto` vem do lote. `largura` e `altura` gravadas pelo `importar.py` (depois do giro do EXIF).
- `lotes` (`nome` PK, `conjunto` com `CHECK` em `treino`/`teste`, `regiao` em JSON ou nula, `importado_em`) substitui o `lotes.yaml`.
- `execucoes` guarda o `anotador` (o nome de `--nome`, a "pasta" de hoje) e o `tipo` (`grounding-dino`, `owlv2`, `yolo`) separados.
- `caixas_revisao` guarda o desfecho como texto (`aceita`, `classe_corrigida`, `classe_atribuida`, `adicionada`), como o registro de hoje, e a `origem` (`candidata` ou nula). As `removidas` não são gravadas: saem da proposta base (imutável) e dos limiares da execução dela, na leitura.
- Classes: a tabela `classes` aceita acréscimo no fim; trocar ou reordenar só se nenhuma `caixas_revisao` existir (a regra de hoje para o `data.yaml`), senão é recusado.

**API do `saida.py`** (os consumidores mudam pouco):
- `abrir(saida, criar=False)`: conexão com `foreign_keys`, `busy_timeout` e a verificação de `user_version`; recusa `imagens.csv` sem `anotacoes.sqlite` (formato anterior). `transacao(con)`: `BEGIN IMMEDIATE` ... `COMMIT`. Uma conexão por chamada pública (abrir é barato), o que também serve às threads do `revisar.py`.
- `preparar(saida, nomes)` substitui o `preparar_saida` do `anotar.py` (pastas, banco, classes, `data.yaml`).
- `ler_estado(saida)` → `{nome: {nome, status, lote, conjunto, voto, motivo, largura, altura}}` (sem a lista de colunas); `gravar_estado` e `registrar_imagem` saem. `registrar(saida, lote, dados_do_lote, [(nome, largura, altura)])` numa transação; o `importar.py` confere as colisões de nome e de `stem` antes de copiar os arquivos e registra depois (interrompido entre os dois, importar de novo recopia).
- `ler_lotes(saida)` mantém o formato `{lote: {conjunto, regiao, importado_em}}`.
- `nova_execucao(saida, anotador, tipo, versao, parametros, classes_hash, agora)` → id; `gravar_proposta(saida, execucao, nome, caixas)` com `caixas = [(nome da classe, confiança, caixa normalizada)]`; `proposta(saida, anotador, nome, proposta_id=None)` → dict `{id, anotador, tipo, versao, parametros, classes, imagem, data, caixas}`, com as caixas já normalizadas (`caixas_normalizadas` passa a devolvê-las direto); `tem_proposta`, `anotadores`, e `propostas_atuais(saida, anotador)` → `{nome: proposta}` numa consulta só, para o `avaliar.py`. `limiares` e `separar` não mudam.
- `revisar(saida, nome, pedido, agora)`: tudo numa transação (conferir o status, a proposta base, inserir a revisão e as caixas, mudar o status), e só depois os arquivos daquela imagem. O pedido aceita `proposta_id`; se vier, tem de ser a proposta vigente do `base` naquela imagem, senão 409 (o anotador gravou uma versão nova enquanto a página estava aberta). `ler_imagem` passa a devolver também `propostas_ids` `{anotador: id}`, e a página o envia no PUT.
- `ler_revisao(saida, nome)`: a revisão vigente, no formato de hoje, com `base.proposta_id`. `aceitar` grava uma revisão `salvar` com `revisor = "aceitar"` e tempo 0.
- `ler_imagem`: a anotação `final` vem da revisão `salvar` vigente das imagens `revisada`, não do `.txt`; `invalidas` fica sempre 0 (a página ainda lê o campo).
- `exportar(saida)`: regenera `data.yaml`, `labels/` (e apaga `.txt` de imagem que não está `revisada`) e `revisadas.txt`. `anotar.py --exportar` e a abertura do `revisar.py` o chamam. `copia_seguranca(saida)` (API `backup`) antes de cada `anotar.py`.

**Consumidores a adaptar:** `importar.py` (registrar; sai o `lotes.yaml`), `anotar.py` (`preparar`, uma execução por rodada, `tem_proposta`, `--sobrescrever` cria versão nova, `--exportar`, cópia de segurança), `avaliar.py` (`carregar_pares` com `propostas_atuais`), `revisar.py` (`main` confere o banco; `proposta_id`), `revisar.html` (envia `proposta_id`), `visualizar.py` (só `ler_estado` sem colunas), o notebook do Colab (copiar o banco para `/content` e de volta), os READMEs (`anotacao/README.md`, seção "Saída" e "Revisão"), e os testes: `test_saida.py` e as fixtures de `test_revisar.py`, `test_avaliar.py`, `test_anotar.py` e `test_importar.py` passam a montar o estado pelo `saida.py`, não por arquivos.

**Ordem sugerida:** `saida.py` com o esquema e `test_saida.py`; `importar.py`; `anotar.py`; `revisar.py` e a página; `avaliar.py` e `visualizar.py`; notebook e READMEs; o teste de concorrência e o manual da seção abaixo. Depois, o T6 sobre o banco.

**Feito (2026-11-13)**, com uma diferença do desenho acima: a anotação `final` que as páginas mostram continua lida do `.txt` de `labels/` (gerado do banco), e não da revisão no banco. Assim o `visualizar.py` ainda abre uma pasta YOLO de outra ferramenta, sem banco, e mostra as linhas inválidas de um `.txt`. Também: `abrir(saida)` não cria o banco (quem cria é `preparar()`), e a cópia `anotacoes.sqlite.bak` é feita só quando o `anotar.py` vai de fato anotar. Verificado: 103 testes (com a escrita concorrente de duas threads e o 409 da proposta trocada), e à mão, sobre as 24 fotos de `tcc-0CF`: importar, anotar com o Grounding DINO e o YOLO, revisar duas pela API (troca de classe e descarte), `avaliar.py` lendo do banco, e uma época de treino do YOLO com o `data.yaml` gerado. O notebook do Colab trabalha numa cópia local e grava de volta no Drive (ida e volta testada localmente).

### Verificação

- pytest do esquema: as `CHECK` recusam estado inválido; `classes` só aceita acréscimo; versão desconhecida é recusada.
- pytest das propostas: anotar duas vezes guarda as duas versões; a revisão aponta para a que viu; uma imagem revisada não volta a pendente.
- pytest da revisão: os mesmos casos de hoje (desfechos, removidas, recusas) sobre o banco; duas sessões na mesma imagem ficam as duas.
- pytest da exportação: `labels/`, `revisadas.txt` e `data.yaml` saem iguais aos do formato atual para o mesmo conteúdo; apagar `labels/` e rodar `--exportar` os recria.
- pytest de concorrência: o servidor numa thread e um `anotar` gravando em outra conexão, sem perda de nenhum dos dois.
- Manual: anotar as fotos de `tcc-0CF`, revisar algumas e treinar uma época do YOLO com o `data.yaml` gerado.

## Fases

A fase 1 muda o formato sem mudar o que o usuário vê; as fases 2 e 3 já entregam uma ferramenta usável (trocar classe e remover caixa, os erros mais comuns hoje); 4 e 5 completam a edição.

| # | Status | Entrega | Verificação |
|---|---|---|---|
| 1 | [x] `8a0253d` | Formato da seção 1 e anotadores da seção 2: `anotar.py --anotador` grava `propostas/<anotador>/` e `imagens.csv`; `--aceitar`; `visualizar.py` mostra propostas (com a confiança) e anotações finais | pytest com propostas sintéticas; o Grounding DINO grava o mesmo que hoje |
| 2 | [x] `ad4170c` | `revisar.py`: servidor e API só de leitura; a página atual servida por ele, com a fila | pytest com o servidor numa thread |
| 3 | [x] `7b123b9` | Edição básica: trocar classe, remover, aceitar, salvar e próxima, descartar (apaga o `.txt`); registro da revisão. `revisadas.txt` e `data.yaml` já vêm da fase 1. Só pendentes são editáveis | pytest da API; teste manual |
| 3b | [x] | Armazenamento em SQLite (seção 6): `anotacoes.sqlite` no lugar de `imagens.csv`, `propostas/` e `revisoes/`; `labels/`, `revisadas.txt` e `data.yaml` gerados do banco; propostas versionadas; `--exportar`. Antes da fase 4, para o registro mudar de formato uma vez só | as da seção 6 |
| 4 | [~] | Caixa por clique sobre as candidatas do anotador e desfazer/refazer (feitos, 2026-11-11; medição no `OBJETIVO.md`). Adiados pela decisão 12: desenhar à mão (arrastar, com lupa), mover e redimensionar (alças, setas, `C` para a próxima candidata sobreposta) e `caixa_ajustada` | pytest da API; teste no Chrome headless pelo protocolo de depuração |
| 5 | [ ] | Reabrir revisadas; atalhos completos da seção 4. O seletor de anotador saiu: desde o T7 (2026-11-15), a edição parte do voto, com as propostas de todos os anotadores | teste manual |

## Decisões

| # | Questão | Recomendação ou decisão |
|---|---|---|
| 1 | ~~Ferramenta própria ou Label Studio?~~ | **Decidido (2026-10-28)**: ferramenta própria, a mais simples possível. |
| 2 | ~~Onde ficam as classes?~~ | **Decidido (2026-11-10)**: `classes.yaml` é a fonte. A lista `nomes` (60 classes TACO e `Background`, na ordem do `best.pt` e de `legado/database`) dá os ids e gera o `data.yaml`; `classes` é o subconjunto que o anotador procura, com prompt e material. Uma classe nova pela página (RF14) entra no fim de `nomes`. |
| 3 | ~~Um ou vários revisores?~~ | **Decidido (2026-10-28)**: um revisor, local. Sem trava por imagem nem identificação por enquanto. |
| 9 | ~~Uma página ou duas?~~ | **Decidido (2026-11-09)**: duas. `visualizar.py` continua gerando a página estática (`file://`, serve no Colab); `revisar.html` é servida pelo `revisar.py` e vira o editor. Aceita-se algum HTML repetido. |
| 10 | ~~Acesso de outro computador (RNF05)?~~ | **Decidido (2026-11-09)**: por enquanto só `127.0.0.1`; uma opção `--host` quando for preciso. |
| 11 | ~~Onde guardar o estado da anotação?~~ | **Decidido (2026-11-11)**: SQLite (`anotacoes.sqlite`, biblioteca padrão) para imagens, propostas e revisões; imagens e rótulos YOLO continuam como arquivos (seção 6). PostgreSQL só com vários revisores em máquinas diferentes (decisão 3); FiftyOne serve para explorar, não substitui a página (decisão 1); DVC, para versionar as bases de treino e teste, entra com o T6/T12 e complementa o banco. |
| 12 | ~~Desenhar caixas à mão agora?~~ | **Decidido (2026-11-11)**: não. Objeto que nenhuma candidata cobre leva ao descarte da imagem. Medir nos registros de revisão a fração de imagens descartadas (`acao: descartar`); se for alta, o desenho à mão volta. |

As decisões 4 a 7 (voto, teste sem classe, mesma classe no voto, sorteio por lote) e a 8 (vidro) são do sistema completo e estão no `OBJETIVO.md`.

## Notas

- Qualidade observada do Grounding DINO (`tiny` e `base`) em fotos de `legado/database/tcc-0CF`: caixas bem localizadas, classes frequentemente erradas (PET transparente como `Glass bottle`; copos e potes de vidro, fora da lista, como tampa ou garrafa plástica). Reforça que trocar classe precisa ser a ação mais rápida.
- Testado em CPU (~10 s por foto de 12 MP no `tiny`) e, depois, na GTX 1650 (CUDA), onde o `avaliar.py` roda as 88 fotos de validação.
- Ambiente de teste usado: venv isolado com torch 2.14.1, transformers 5.21.0 (Python 3.14).
