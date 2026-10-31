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
- `testes_serial.py` lê a porta do `config.json` (`05666aa`).

### Frontend

- **Cancelas:** o vidro usa a chave `glass` (com `vidro`, ele nunca acionava depois de salvar), os ângulos padrão são os do backend (50/150/130/110) e o texto não manda mais reiniciar o backend (`1b7cfbd`).
- **Câmera por URL:** o campo aceita URL de stream além do índice (`9601534`).
- **Seletor de modelo** lista os pesos TACO reais, com `best.pt` como padrão; antes oferecia o `yolov8s.pt` (COCO) e arquivos inexistentes (`cbdf60a`).
- **Status do Monitor:** mostra a porta serial real (ou "Demo"), e câmera/YOLO só aparecem ativos quando chegam quadros (`2cbf56f`).
- **Backend offline:** "Salvar" desabilitado (`026269d`); as páginas de configuração ficam bloqueadas, e os botões da esteira exigem serial (`5b24934`).

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
- **Logs** com `logging` (hora, nível, thread); `ECOVISION_LOG=DEBUG` mostra cada comando ao ESP32 e as detecções de cada quadro (`fa797e9`, `c313f8d`).
- **Versões fixadas** (`==`) em `backend/requirements*.txt`, testadas com Python 3.14; o mínimo passa a ser Python 3.12 (`3acfb23`).

## 5. Testes

- 25 testes pytest para `deteccao.py`, inclusive se toda classe do `best.pt` tem material (`7e54bfc`), e `test_requirements.py`, que confere as versões fixadas (`3acfb23`). Rodar com `python -m pytest backend/tests`.

## Ainda como na tese

- O acionamento não acompanha a posição do objeto na esteira (5 s fixos por objeto). Fica para um módulo de rastreamento, fora da refatoração.
- `docs/diagrams/` ainda descreve a arquitetura proposta na tese; os diagramas serão refeitos com os módulos novos.
- O login continua simulado.
