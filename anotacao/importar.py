"""
Importa um lote de imagens para o armazenamento comum da anotação (OBJETIVO.md,
seção 6, tarefa T5).

Cada imagem é gravada uma vez em <saida>/images/<lote>_<nome> e registrada no
banco (<saida>/anotacoes.sqlite, formato em saida.py) como pendente, com o seu
conjunto (treino ou teste), no lote: a importação, que guarda a região de
interesse e a data. Todos os anotadores (anotar.py) leem de lá; nenhum copia
imagens.

A imagem muda o mínimo: só é regravada se o EXIF a gira (as caixas têm de valer
para a imagem girada em qualquer leitor) ou se passa de --lado-maximo; fora
isso, cópia byte a byte (recomprimir um JPEG perde qualidade). Sem normalizar
cor nem recortar: a base de treino tem de parecer com o que a câmera vê na
operação.

Conjunto: sorteado imagem a imagem pelo hash do nome final (<lote>_<nome>),
cerca de 1 em cada 10 para o teste (decisão 7, revista em 2026-11-15), sempre
o mesmo para o mesmo nome; --conjunto força o de todas as imagens da
importação. Sortear por imagem só não vaza cenas entre treino e teste porque
a captura (T4) não grava quadros próximos demais. Uma vez gravado, o conjunto
de uma imagem não muda. As de teste são revisadas sem pré-anotação.

Proximidade no tempo (T4, decisão 7): o horário de captura de cada imagem vem
do EXIF (DateTimeOriginal, com SubSecTimeOriginal e OffsetTimeOriginal, como
o backend grava; sem fuso, hora local), senão do nome no padrão das câmeras
de celular (20250503_140329.jpg, hora local). É lido do arquivo de origem,
antes de qualquer regravação, e fica no banco (imagens.capturada_em, em UTC).
Imagens a menos de --janela segundos uma da outra (em cadeia, contando as já
importadas) formam um grupo e vão todas ao mesmo conjunto: o das já
importadas do grupo, senão o sorteio pelo nome da primeira. São listadas no
relatório; um grupo com imagens nos dois conjuntos (já importadas assim, ou
por --conjunto) gera um aviso. Sem horário, o sorteio por imagem.

Uso:
    python anotacao/importar.py fotos/*.jpg -o anotacoes --lote 2026-11-11a
    python anotacao/importar.py fotos/ -o anotacoes --lote validacao-0CF --conjunto teste \\
        --regiao 0 0.1 1 0.9 --link
    python anotacao/importar.py capturas/20261115T230000Z/ -o anotacoes --lote 2026-11-15b \\
        --janela 15
"""

import argparse
import hashlib
import os
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image, ImageOps

import saida as formato
from anotar import DIR_SCRIPT, TAG_ORIENTACAO_EXIF, carregar_nomes

CONJUNTOS = formato.CONJUNTOS
FRACAO_TESTE = 10  # 1 imagem em cada 10 vai para o teste (decisão 7, revista em 2026-11-15)
LOTE_VALIDO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]*$")
QUALIDADE_JPEG = 95
JANELA_S = 10  # Δ: imagens mais próximas que isso vão ao mesmo conjunto (PLANO-CAPTURA.md)

# Tags EXIF do horário (as que o backend grava, backend/captura.py)
TAG_DATETIME = 0x0132
TAG_IFD_EXIF = 0x8769
TAG_DATETIME_ORIGINAL = 0x9003
TAG_OFFSET_TIME_ORIGINAL = 0x9011
TAG_SUBSEC_TIME_ORIGINAL = 0x9291
# 20250503_140329.jpg, o nome padrão das câmeras de celular (as fotos de
# legado/database perderam o EXIF na exportação, mas não o nome)
NOME_COM_HORARIO = re.compile(r"(?<!\d)(20\d{6})_(\d{6})(?!\d)")
FUSO_EXIF = re.compile(r"^([+-])(\d{2}):(\d{2})$")


def sortear_conjunto(nome):
    """'teste' para cerca de 1 imagem em cada FRACAO_TESTE, sempre o mesmo para o mesmo nome."""
    valor = int.from_bytes(hashlib.sha256(nome.encode("utf-8")).digest()[:8], "big")
    return "teste" if valor % FRACAO_TESTE == 0 else "treino"


def _texto_exif(valor):
    return valor.strip().rstrip("\x00").strip() if isinstance(valor, str) else ""


def horario_exif(imagem):
    """
    Horário de captura no EXIF de uma imagem aberta, em UTC; None sem ele.
    DateTimeOriginal (com os milissegundos e o fuso, se houver), senão
    DateTime; sem fuso, hora local.
    """
    exif = imagem.getexif()
    ifd = exif.get_ifd(TAG_IFD_EXIF)
    original = _texto_exif(ifd.get(TAG_DATETIME_ORIGINAL))
    texto = original or _texto_exif(exif.get(TAG_DATETIME))
    try:
        horario = datetime.strptime(texto, "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None
    if original:  # a fração e o fuso acompanham o DateTimeOriginal
        fracao = _texto_exif(ifd.get(TAG_SUBSEC_TIME_ORIGINAL))
        if fracao.isdigit():
            horario = horario.replace(microsecond=int(fracao[:6].ljust(6, "0")))
        fuso = FUSO_EXIF.match(_texto_exif(ifd.get(TAG_OFFSET_TIME_ORIGINAL)))
        if fuso:
            sinal = -1 if fuso[1] == "-" else 1
            horario = horario.replace(tzinfo=timezone(
                sinal * timedelta(hours=int(fuso[2]), minutes=int(fuso[3]))))
    return horario.astimezone(timezone.utc)  # sem fuso, astimezone a toma como local


def horario_nome(nome):
    """Horário de captura pelo nome (20250503_140329.jpg, hora local), em UTC; None sem ele."""
    achado = NOME_COM_HORARIO.search(nome)
    if not achado:
        return None
    try:
        horario = datetime.strptime(achado[1] + achado[2], "%Y%m%d%H%M%S")
    except ValueError:
        return None
    return horario.astimezone(timezone.utc)


def horario_captura(arquivo):
    """Horário de captura do arquivo, em UTC: o do EXIF, senão o do nome; None sem nenhum."""
    try:
        with Image.open(arquivo) as imagem:
            horario = horario_exif(imagem)
    except OSError:
        horario = None
    return horario or horario_nome(Path(arquivo).name)


def agrupar_por_horario(novas, existentes, janela, conjunto=None):
    """
    Conjunto de cada imagem nova pela proximidade no tempo (decisão 7).

    novas: [(nome, horario ou None)]; existentes: [(nome, horario ou None,
    conjunto)], as já importadas. Em ordem de horário, imagens a menos de
    janela segundos da anterior (em cadeia) formam um grupo. A nova de um grupo
    recebe conjunto, se dado; senão o das já importadas do grupo (havendo as
    duas, o da mais próxima no tempo); senão o sorteio pelo nome da primeira
    nova do grupo. Sem horário, ou sozinha, o sorteio pelo próprio nome.

    Devolve ({nome: conjunto} das novas, [grupos com nova e mais de uma
    imagem, cada um a lista de nomes em ordem de horário], [avisos]).
    """
    com_horario = sorted([(h, n, None) for n, h in novas if h is not None]
                         + [(h, n, c) for n, h, c in existentes if h is not None],
                         key=lambda x: (x[0], x[1]))
    grupos, anterior = [], None
    for item in com_horario:
        if anterior is None or (item[0] - anterior).total_seconds() >= janela:
            grupos.append([])
        grupos[-1].append(item)
        anterior = item[0]

    conjuntos = {n: conjunto or sortear_conjunto(n) for n, h in novas if h is None}
    proximos, avisos = [], []
    for grupo in grupos:
        novas_grupo = [n for _, n, c in grupo if c is None]
        if not novas_grupo:
            continue
        antigas = [(h, c) for h, _, c in grupo if c is not None]
        for h, n, c in grupo:
            if c is not None:
                continue
            if conjunto:
                conjuntos[n] = conjunto
            elif antigas:  # a já importada mais próxima no tempo (empate: a anterior)
                conjuntos[n] = min(antigas, key=lambda a: abs((a[0] - h).total_seconds()))[1]
            else:
                conjuntos[n] = sortear_conjunto(novas_grupo[0])
        if len(grupo) > 1:
            nomes = [n for _, n, _ in grupo]
            proximos.append(nomes)
            if len({c or conjuntos[n] for _, n, c in grupo}) > 1:
                avisos.append("imagens a menos de {:g} s uma da outra em conjuntos diferentes: "
                              "{}".format(janela, ", ".join(
                                  f"{n} ({c or conjuntos[n]})" for _, n, c in grupo)))
    return conjuntos, proximos, avisos


def validar_regiao(regiao):
    """[x1, y1, x2, y2] normalizada, com 0 <= x1 < x2 <= 1 e o mesmo em y; None passa."""
    if regiao is None:
        return None
    x1, y1, x2, y2 = (float(v) for v in regiao)
    if not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
        raise ValueError(f"região de interesse inválida: {regiao} (normalizada, x1 < x2, y1 < y2)")
    return [x1, y1, x2, y2]


def listar_arquivos(entradas):
    """Arquivos de imagem das entradas (arquivos ou pastas, sem descer em subpastas)."""
    arquivos = []
    for entrada in map(Path, entradas):
        if entrada.is_dir():
            arquivos += sorted(p for p in entrada.iterdir()
                               if p.is_file() and p.suffix.lower() in formato.EXTENSOES_IMAGEM)
        elif entrada.is_file():
            arquivos.append(entrada)
        else:
            raise ValueError(f"não encontrado: {entrada}")
    return arquivos


def gravar_imagem(origem, destino, lado_maximo=None, link=False):
    """
    Grava origem em destino. Regrava (JPEG com qualidade 95, sem EXIF) só se o
    EXIF gira a imagem ou se ela passa de lado_maximo; senão, cópia byte a
    byte, ou link com link=True (hardlink; simbólico se o hardlink não for
    possível). Devolve como gravou: 'regravada', 'copia' ou 'link'.
    """
    destino.unlink(missing_ok=True)  # sobra de uma importação interrompida
    with Image.open(origem) as imagem:
        girada = imagem.getexif().get(TAG_ORIENTACAO_EXIF, 1) != 1
        grande = lado_maximo is not None and max(imagem.size) > lado_maximo
        if girada or grande:
            imagem = ImageOps.exif_transpose(imagem)
            if grande:
                imagem.thumbnail((lado_maximo, lado_maximo), Image.Resampling.LANCZOS)
            if destino.suffix.lower() in (".jpg", ".jpeg"):
                imagem.convert("RGB").save(destino, quality=QUALIDADE_JPEG)
            else:
                imagem.save(destino)
            return "regravada"
    if link:
        try:
            os.link(origem, destino)
        except OSError:  # outro sistema de arquivos, ou sem suporte a hardlink
            os.symlink(Path(origem).resolve(), destino)
        return "link"
    shutil.copy2(origem, destino)
    return "copia"


def importar(saida, arquivos, lote, nomes_classes, conjunto=None, regiao=None,
             lado_maximo=None, link=False, agora=None, janela=JANELA_S):
    """
    Importa arquivos como o lote dado. Uma imagem já importada (mesmo nome final)
    é pulada, e o conjunto dela não muda. Cada imagem nova recebe conjunto, se
    dado, ou o do seu grupo de imagens a menos de janela segundos
    (agrupar_por_horario), ou o sorteio pelo nome final. A região de um lote já
    existente não muda; pedir outra é erro. Devolve {'importadas': [...],
    'puladas': [...], 'conjuntos': {conjunto: quantas das importadas},
    'sem_horario': quantas das importadas, 'proximas': [[nomes] por grupo],
    'avisos': [...]}.
    """
    saida = Path(saida)
    if not LOTE_VALIDO.match(lote):
        raise ValueError(f"nome de lote inválido: '{lote}' (letras, dígitos, '.' e '-'; "
                         "sem '_', que separa o lote do nome da imagem)")
    if conjunto is not None and conjunto not in CONJUNTOS:
        raise ValueError(f"conjunto deve ser um de {', '.join(CONJUNTOS)}")
    regiao = validar_regiao(regiao)
    if janela < 0:
        raise ValueError("a janela não pode ser negativa")

    formato.preparar(saida, nomes_classes)
    lotes = formato.ler_lotes(saida)
    if lote in lotes:
        dados_lote = lotes[lote]
        if regiao is not None and regiao != dados_lote.get("regiao"):
            raise ValueError(f"o lote {lote} já tem região {dados_lote.get('regiao')}")
    else:
        dados_lote = {"regiao": regiao, "importado_em": agora or formato.agora_iso()}

    estado = formato.ler_estado(saida)
    nomes = [f"{lote}_{a.name}" for a in arquivos]
    repetidos = sorted({n for n in nomes if nomes.count(n) > 1})
    if repetidos:
        raise ValueError(f"nomes repetidos na entrada: {', '.join(repetidos)}")
    formato.conferir_colisoes(estado, nomes)  # antes de copiar qualquer arquivo

    # O horário vem da origem, antes de regravar (a regravação descarta o EXIF)
    horarios = {nome: horario_captura(arquivo)
                for arquivo, nome in zip(arquivos, nomes) if nome not in estado}
    existentes = [(n, None if r["capturada_em"] is None
                   else datetime.fromisoformat(r["capturada_em"]), r["conjunto"])
                  for n, r in estado.items()]
    conjuntos, proximas, avisos = agrupar_por_horario(list(horarios.items()), existentes,
                                                     janela, conjunto)

    novas, puladas = [], []
    for arquivo, nome in zip(arquivos, nomes):
        if nome in estado:
            puladas.append(nome)
            continue
        destino = saida / "images" / nome
        gravar_imagem(arquivo, destino, lado_maximo, link)
        horario = horarios[nome]
        novas.append((nome, *formato.tamanho_imagem(destino), conjuntos[nome],
                      None if horario is None else horario.isoformat()))

    # Os arquivos antes do banco: interrompido entre os dois, as imagens ficam
    # sem registro, e importar de novo as grava outra vez e registra
    importadas = formato.registrar(saida, novas, lote, dados_lote, agora)
    contagem = {c: sum(1 for n, _, _, cc, _ in novas if cc == c and n in importadas)
                for c in CONJUNTOS}
    return {"importadas": importadas, "puladas": puladas, "conjuntos": contagem,
            "sem_horario": sum(1 for n in importadas if horarios[n] is None),
            "proximas": proximas, "avisos": avisos}


def resumo(lote, resultado):
    """Uma linha sobre a importação: quantas, em que conjunto, quantas puladas."""
    c = resultado["conjuntos"]
    linha = (f"Lote {lote}: {len(resultado['importadas'])} imagem(ns) importada(s) "
             f"({c['treino']} de treino, {c['teste']} de teste), "
             f"{len(resultado['puladas'])} já importada(s)")
    if resultado.get("sem_horario"):
        linha += f", {resultado['sem_horario']} sem horário de captura"
    return linha


def relatorio(resultado, janela):
    """Linhas sobre as imagens próximas no tempo e os avisos (vazio se não há nada)."""
    linhas = []
    if resultado["proximas"]:
        linhas.append(f"Imagens a menos de {janela:g} s de outra (cada grupo vai a um "
                      f"conjunto só): {len(resultado['proximas'])} grupo(s)")
        linhas += ["  " + ", ".join(grupo) for grupo in resultado["proximas"]]
    linhas += [f"Aviso: {aviso}" for aviso in resultado["avisos"]]
    return linhas


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Importa um lote de imagens para o armazenamento comum da anotação.")
    parser.add_argument("entradas", nargs="+", help="imagens ou pastas de imagens")
    parser.add_argument("-o", "--saida", type=Path, default=Path("anotacoes"),
                        help="diretório de saída (padrão: ./anotacoes)")
    parser.add_argument("--lote", required=True,
                        help="nome do lote de captura (letras, dígitos, '.' e '-')")
    parser.add_argument("--conjunto", choices=CONJUNTOS,
                        help="força o conjunto de todas as imagens importadas (padrão: "
                             "sorteio pelo nome de cada uma, 1 em 10 para o teste, e o "
                             "mesmo conjunto para as próximas no tempo)")
    parser.add_argument("--janela", type=float, default=JANELA_S,
                        help="Δ em segundos: imagens capturadas a menos disso uma da outra "
                             f"vão ao mesmo conjunto; 0 desliga (padrão: {JANELA_S})")
    parser.add_argument("--regiao", type=float, nargs=4, metavar=("X1", "Y1", "X2", "Y2"),
                        help="região de interesse do lote, normalizada (0 a 1): os "
                             "anotadores descartam caixas com o centro fora dela")
    parser.add_argument("--lado-maximo", type=int,
                        help="reduz imagens com o lado maior acima disso (padrão: não reduz)")
    parser.add_argument("--link", action="store_true",
                        help="link em vez de cópia, quando a imagem não precisa ser regravada")
    parser.add_argument("--classes", type=Path, default=DIR_SCRIPT / "classes.yaml",
                        help="lista de classes, para o banco e o data.yaml (padrão: "
                             "anotacao/classes.yaml)")
    args = parser.parse_args(argv)
    if args.lado_maximo is not None and args.lado_maximo < 32:
        parser.error("--lado-maximo pequeno demais")
    if args.janela < 0:
        parser.error("--janela não pode ser negativa")

    arquivos = listar_arquivos(args.entradas)
    if not arquivos:
        parser.error("nenhuma imagem nas entradas")
    resultado = importar(args.saida, arquivos, args.lote, carregar_nomes(args.classes),
                         args.conjunto, args.regiao, args.lado_maximo, args.link,
                         janela=args.janela)
    print(f"{resumo(args.lote, resultado)} em {args.saida.resolve()}")
    for linha in relatorio(resultado, args.janela):
        print(linha)


if __name__ == "__main__":
    try:
        main()
    except ValueError as erro:
        sys.exit(f"Erro: {erro}")
