# Mudanças desde a tese

O que mudou em relação à versão final do TCC, marcada pela tag `tese-final` (`vitor-scosta/Ecovision@d6f5181`). Para ver o código da tese: `git show tese-final:<caminho>`; para ver o que mudou num arquivo: `git diff tese-final -- <caminho>`. Cada item cita o commit.

**Estado:** as mudanças da refatoração (seções 2 a 5) estão na branch `feature/refactoring-original-code` e foram testadas sem hardware (ESP32 simulado num pty, fotos de `legado/` como câmera). A verificação com ESP32, câmera e interface é feita antes do merge, pelos blocos A a F do `REFATORACAO.md`. O firmware novo precisa ser regravado no ESP32 (`cd firmware && pio run -t upload`).

## 1. Repositório (2026-10-10 a 2026-10-20)

- A versão preliminar (`vitor-scosta/tcc-testes`) foi para `legado/` e a final (`vitor-scosta/Ecovision`) virou a raiz, com os dois históricos preservados (`727bdaf`, `e9f470b`). O código da final foi organizado em `frontend/`, `backend/` e `firmware/` (`ef7afa4`).
- `ecovision_local_modf.py` passou a ser o backend oficial, e o README foi dividido em um por pasta (`b7f8cc3`). `PROBLEMAS.md` foi para a raiz (`7007a0e`) e hoje guarda só problemas fora do código (`39b7b70`).
- `backend/config.json` deixou de ser versionado: é local de cada máquina e é criado com os padrões na primeira execução (`79ebc1e`). `.gitignore` cobre `.venv/` e `*.cache` (`3f4f909`).

## 2. Correções de comportamento

### Backend

- **Configuração pela UI:** o backend responde `get_config`, então os painéis mostram os valores reais em vez de padrões fixos, e "Salvar" não grava mais `model_path` vazio (que fazia o próximo start falhar) nem a chave `type` (`de008c6`).
- **Esteira não religa sozinha:** ao fim de um acionamento, o motor fica como o usuário deixou (`1ca641f`).
- **Câmera que falha** (URL errada, Wi-Fi) é reaberta a cada 5 s, em vez de a thread do YOLO morrer com o servidor no ar e sem vídeo (`f80bb71`).
- **Mapa TACO → material** cobre todas as classes do `best.pt` (`carded blister pack` fica `other`) e perdeu a chave morta `plastic glooves` (`3875788`).
- **FPS** medido em janelas de 1 s, em vez da média desde o início (`bc24683`).
- **Serial:** escrita com trava, e ninguém espera resposta; uma thread registra tudo o que o ESP32 envia. Antes, a thread do YOLO e o WebSocket escreviam sem trava, e a leitura bloqueava o loop por até 1,5 s e podia ler a resposta de outro comando (`2701579`).
- **Envio dos quadros:** um cliente lento perde quadros em vez de acumular envios e atrasar os outros; sem cliente conectado, o quadro nem é codificado (`c519981`).
- **Confiança vale na hora:** o modelo roda com piso 0,1 e o filtro por `confidence` é feito a cada quadro; antes, o slider só valia depois de reiniciar (`ed0e5c2`).
- **Estado do motor:** começa desligado e só muda quando o comando sai pela serial; antes, começava ligado e mudava até em modo demonstração, e o Monitor mostrava a esteira ligada sem ESP32. Quando o ESP32 reinicia (ex.: queda de tensão com o servo), o backend lê `ESP32 pronto.` e marca o motor desligado, como ele de fato fica (`403c5e1`).
- **`config.json` de versão anterior** sem alguma chave (ex.: `class_to_angle`) usa o padrão dela, com um aviso no log; antes dava `KeyError` no laço da câmera a cada 5 s (`5fe875b`).
- **Serial reconecta:** a porta é reaberta a cada 5 s, na partida e depois de uma queda (cabo USB mexido); antes, o backend ficava em modo demonstração até reiniciar. Uma reconexão não religa a esteira (`9e83f65`).
- `testes_serial.py` lê a porta do `config.json` (`05666aa`).

### Frontend

- **Cancelas:** o vidro usa a chave `glass` (com `vidro`, ele nunca acionava depois de salvar), os ângulos padrão são os do backend (50/150/130/110) e o texto não manda mais reiniciar o backend (`1b7cfbd`).
- **Câmera por URL:** o campo aceita URL de stream além do índice (`9601534`).
- **Seletor de modelo** lista os pesos TACO reais, com `best.pt` como padrão; antes oferecia `yolov8l`/`yolov8x`, que não existem, e não oferecia o `best.pt` (`cbdf60a`). O `yolov8s.pt` ficou fora da lista por ser tido como COCO; é TACO (veja `yolo_models/README.md`).
- **Status do Monitor:** mostra a porta serial real (ou "Demo"), e câmera/YOLO só aparecem ativos quando chegam quadros (`2cbf56f`).
- **Backend offline:** "Salvar" desabilitado (`026269d`); as páginas de configuração ficam bloqueadas, e os botões da esteira exigem serial (`5b24934`).
- **"Testar Conexão Serial"** devolve o motor ao estado em que estava (antes, sempre terminava em `MOTOR OFF`, parando a esteira que estava andando) e exige a serial ativa (`9e83f65`).
- **Badge de conexão ao trocar de painel:** um painel aberto com o socket já conectado mostrava "Backend Offline" (e bloqueava "Salvar") até o backend reconectar; o estado agora vem do socket compartilhado ao montar, e os listeners do socket não ficam mais órfãos ao sair do painel (`4052b4e`).

### Firmware

- Comando inválido responde `ERR: ...` e não move o servo (antes, `PING` virava 0°); ângulos fora de 0..180 são recusados; `PING` → `PONG`; o servo vai para 175° no boot; o LED da placa acende com o motor e pisca durante cada acionamento (`1f08106`).

## 3. Limpeza (sem mudança de comportamento)

- Backend: prints de debug por quadro e atalhos de teclado inexistentes removidos (`4a6ebd0`); variante antiga `ecovision_local.py` apagada (`5198a85`, está em `git show tese-final:backend/ecovision_local.py`).
- Firmware: versão antiga comentada e rampas de PWM mortas removidas (`55fd7da`).
- Frontend: 40 componentes, 34 dependências e imports sem uso do export do Figma removidos (`667766a`); dependências `"*"` fixadas, com `package-lock.json` (`51435e4`); `vite` só em `devDependencies` (`b5246b4`).

## 4. Padronização

- **Lógica de detecção** separada em `backend/deteccao.py`, sem câmera, serial nem YOLO (`53d7b51`).
- **Frontend:** URL do backend em `src/config.ts`, badge de conexão único (`BadgeBackend`) e ícone das detecções pelo material enviado pelo backend (`dd09a68`).
- **Caixas** desenhadas só pelo frontend, com label de classe, material e confiança do tamanho do texto; antes, cv2 e canvas desenhavam as duas (`822aceb`).
- **Logs** com `logging` (hora, nível, thread); `--debug=true` mostra cada comando ao ESP32 e as detecções de cada quadro, também via `run.sh`/`run.bat` (`fa797e9`, `6892bb2`; antes era a variável `ECOVISION_LOG=DEBUG`).
- **Versões fixadas** (`==`) em `backend/requirements*.txt`, testadas com Python 3.14; o mínimo passa a ser Python 3.12 (`3acfb23`).

## 5. Testes

- 25 testes pytest para `deteccao.py`, inclusive se toda classe do `best.pt` tem material (`7e54bfc`), e `test_requirements.py`, que confere as versões fixadas (`3acfb23`). Testes do estado do motor (`motor.py`, `403c5e1`), da captura (`captura.py`, `5fe875b`) e da câmera (`camera.py`, com uma câmera falsa, `6316da1`). Rodar com `python -m pytest backend/tests`.

## 6. Recursos novos

- **Captura para a anotação** (T4 do `OBJETIVO.md`): com `--capturar=true` ou `captura.ativa`, o backend grava quadros da esteira espaçados no tempo (no mínimo a cada `intervalo_s`; com o motor desligado, só quando a cena muda), em JPEG com o horário UTC no EXIF, mais um `captura.jsonl` por sessão. Desligada por padrão; não muda a detecção nem o acionamento. Pillow passa a ser dependência fixada (`5fe875b`; detalhes no `backend/README.md`).
- **Câmera configurada** (T4, etapa 6a, `6316da1`): o backend abre a câmera ele mesmo (`camera.py`, V4L2 no Linux) e aplica o bloco `camera` do `config.json` (formato, resolução, fps, exposição, ganho, temperatura de cor, foco, `imgsz`), confere o que a câmera aceitou e registra tudo no log e no `captura.jsonl`. `null` em exposição, cor e foco religa o automático a cada abertura. Uma thread lê a câmera e guarda só o quadro mais recente, como fazia o Ultralytics; um vídeo como câmera é lido no seu ritmo. Sem o bloco, a câmera abre como antes. `ajustar_camera.py` lista formatos com o fps medido e varre exposição, cor, foco, ganho e os controles de imagem (brilho, contraste, saturação, nitidez, gama, também no bloco, para corrigir a imagem azulada com que a câmera da esteira liga). No Windows (DSHOW), sem teste (detalhes no `backend/README.md`).
- **Janela Δ na importação** (T4, `40e76d5`): o `anotacao/importar.py` lê o horário de captura (EXIF, senão o nome das fotos de celular) e põe no mesmo conjunto (treino ou teste) as imagens a menos de `--janela` segundos uma da outra, contando as já importadas; avisa se um grupo já estava nos dois conjuntos. O banco da anotação passa ao esquema v7 (`imagens.capturada_em`); saídas v6 são recusadas e têm de ser reimportadas (detalhes no `anotacao/README.md`).

## Ainda como na tese

- O acionamento não acompanha a posição do objeto na esteira (5 s fixos por objeto). Fica para um módulo de rastreamento, fora da refatoração.
- `docs/diagrams/` ainda descreve a arquitetura proposta na tese; os diagramas serão refeitos com os módulos novos.
- O login continua simulado.
