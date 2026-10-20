# Problemas conhecidos — fora do código

Problemas que continuam valendo e que não são bugs do backend, do frontend ou do firmware: repositório, dados, modelo e montagem física. As limitações do sistema em funcionamento estão em [`README.md`](README.md#limitações-conhecidas).

> **Histórico:** este arquivo nasceu de uma análise de 2026-10-08 sobre a versão preliminar do TCC (hoje em [`legado/`](legado/)) e sobre o texto da monografia. Os itens resolvidos pela versão final, os que só afetavam o código de `legado/` (que não é mais executado) e as observações sobre a monografia (já entregue) foram removidos. A análise completa, com a numeração original (E1–E5, M1–M7, P1–P11, T1–T12), está em `git show 7007a0e:PROBLEMAS.md`. Os códigos abaixo mantêm essa numeração.

**Níveis de complexidade:** 🟢 pontual · 🟡 moderado · 🔴 estrutural

---

## Modelo e dados

### 🔴 T2. A avaliação do fine-tuning provavelmente tem vazamento de dados

- As fotos da equipe (`legado/database/`) mostram **as mesmas cenas** em 4 condições de captura, tiradas com segundos de diferença (ex.: `45CF 14:18:21`, `0CF 14:18:29`, `0SF 14:18:39`, `45SF 14:18:49`): a mesma disposição de objetos, só com ângulo de câmera (0°/45°) ou flash diferentes.
- O fine-tuning usou essas ~100 imagens com split aleatório 80/20. Quase certamente a mesma cena aparece no treino e na validação, o que deixa as métricas **otimistas**: precisão ~0,78 e mAP50 ~0,80 na monografia, e mAP50 de 0,995 no checkpoint do `best.pt`, que continuou o treino sobre o mesmo split (veja [`yolo_models/README.md`](yolo_models/README.md)). A validação também tem só ~18-20 imagens.
- **Correção, se houver retreino:** dividir treino e validação **por cena**, agrupando as 4 fotos da mesma cena, e reavaliar. O script de treino e o split usado não estão no repositório.
- ❓ O split foi aleatório por imagem no Roboflow? Foi usado `freeze` (a monografia diz que só as camadas finais foram treinadas, mas o Ultralytics treina todas por padrão)?

### 🟢 M6. `legado/database/*/YOLO_dataset/data.yaml`: `path:` absoluto do Windows

- O caminho `C:/Users/vitor/Documents/...` faz qualquer treino ou validação com essas fotos falhar em outra máquina.
- Só importa se as fotos forem reaproveitadas, por exemplo no retreino do T2.
- **Correção:** remover o `path:` ou torná-lo relativo.

### 🟢 M1. A planilha de avaliação tem as colunas por classe trocadas

- `legado/scripts/avaliacao_modelos_resultados_2.xlsx` foi gerada por `legado/scripts/val.py:59`, que lê `metrics.box.p[idx]` na ordem `[6, 33, 17, 12, 7, 5]`, mas o Ultralytics devolve as classes na ordem crescente de `ap_class_index` (5, 6, 7, 12, 17, 33).
- Resultado provável: as colunas mostram a classe errada (só `metal drink can` coincide). As médias, usadas na monografia, não são afetadas.
- Só importa se a planilha for usada de novo. ❓ Não confirmado por execução: rode `print(metrics.box.ap_class_index)`.
- **Correção:** `i = list(metrics.box.ap_class_index).index(class_id)` e então `metrics.box.class_result(i)`.

## Montagem física

### 🟡 M3. A geometria entre câmera e desviador não é considerada

- O backend aciona o servo no instante em que o centro do objeto cruza a faixa da ROI, com a esteira em movimento, e segura a posição por um tempo fixo (`servo_actuation_seconds`).
- Se o desviador não estiver logo abaixo da faixa da ROI, falta um atraso de transporte (distância ÷ velocidade). É a limitação "o acionamento não acompanha a posição do objeto" do [`README.md`](README.md#limitações-conhecidas).
- ❓ Qual é a distância entre a faixa da ROI e o servo, e qual é a velocidade da esteira (PWM fixo em 255)? Esses dois números são o ponto de partida da correção.

## Repositório

### 🔴 E4. Repositório pesado: ~860 MB de `.git`

- As fotos de `legado/database/` têm cerca de 9,5 MB cada (resolução de celular), e cada uma está gravada **3 vezes**: em `COCO_dataset/`, em `YOLO_dataset/validation/images/` e uma versão menor em `.thumbnail/`.
- Os pesos `.pt` estão no git sem LFS: cerca de 206 MB em `yolo_models/taco/` e 83 MB em `legado/yolo_models/`.
- Encolher o histórico exige reescrevê-lo (`git lfs migrate` ou `git filter-repo`), o que muda todos os hashes, inclusive o da tag `tese-final`. **Recomendação:** não reescrever. Daqui em diante, não versionar pesos ou fotos novos direto no git; usar LFS ou armazenamento externo. Redimensionar as fotos para ~1280 px não altera o resultado com `imgsz=640`.

---

## Dúvidas em aberto

1. **Geometria:** distância entre a faixa da ROI e o servo, e velocidade da esteira (M3).
2. **Fine-tuning:** o split foi aleatório por imagem? Usou `freeze`? (T2)
3. **Planilha:** confirmar a ordem com `print(metrics.box.ap_class_index)` (M1).
