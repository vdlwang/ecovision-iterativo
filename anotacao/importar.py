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

Uso:
    python anotacao/importar.py fotos/*.jpg -o anotacoes --lote 2026-11-11a
    python anotacao/importar.py fotos/ -o anotacoes --lote validacao-0CF --conjunto teste \\
        --regiao 0 0.1 1 0.9 --link
"""

import argparse
import hashlib
import os
import re
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageOps

import saida as formato
from anotar import DIR_SCRIPT, TAG_ORIENTACAO_EXIF, carregar_nomes

CONJUNTOS = formato.CONJUNTOS
FRACAO_TESTE = 10  # 1 imagem em cada 10 vai para o teste (decisão 7, revista em 2026-11-15)
LOTE_VALIDO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]*$")
QUALIDADE_JPEG = 95


def sortear_conjunto(nome):
    """'teste' para cerca de 1 imagem em cada FRACAO_TESTE, sempre o mesmo para o mesmo nome."""
    valor = int.from_bytes(hashlib.sha256(nome.encode("utf-8")).digest()[:8], "big")
    return "teste" if valor % FRACAO_TESTE == 0 else "treino"


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
             lado_maximo=None, link=False, agora=None):
    """
    Importa arquivos como o lote dado. Uma imagem já importada (mesmo nome final)
    é pulada, e o conjunto dela não muda. Cada imagem nova recebe conjunto, se
    dado, ou o sorteio pelo nome final. A região de um lote já existente não
    muda; pedir outra é erro. Devolve {'importadas': [...], 'puladas': [...],
    'conjuntos': {conjunto: quantas das importadas}}.
    """
    saida = Path(saida)
    if not LOTE_VALIDO.match(lote):
        raise ValueError(f"nome de lote inválido: '{lote}' (letras, dígitos, '.' e '-'; "
                         "sem '_', que separa o lote do nome da imagem)")
    if conjunto is not None and conjunto not in CONJUNTOS:
        raise ValueError(f"conjunto deve ser um de {', '.join(CONJUNTOS)}")
    regiao = validar_regiao(regiao)

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

    novas, puladas = [], []
    for arquivo, nome in zip(arquivos, nomes):
        if nome in estado:
            puladas.append(nome)
            continue
        destino = saida / "images" / nome
        gravar_imagem(arquivo, destino, lado_maximo, link)
        novas.append((nome, *formato.tamanho_imagem(destino), conjunto or sortear_conjunto(nome)))

    # Os arquivos antes do banco: interrompido entre os dois, as imagens ficam
    # sem registro, e importar de novo as grava outra vez e registra
    importadas = formato.registrar(saida, novas, lote, dados_lote, agora)
    conjuntos = {c: sum(1 for n, *_, cc in novas if cc == c and n in importadas)
                 for c in CONJUNTOS}
    return {"importadas": importadas, "puladas": puladas, "conjuntos": conjuntos}


def resumo(lote, resultado):
    """Uma linha sobre a importação: quantas, em que conjunto, quantas puladas."""
    c = resultado["conjuntos"]
    return (f"Lote {lote}: {len(resultado['importadas'])} imagem(ns) importada(s) "
            f"({c['treino']} de treino, {c['teste']} de teste), "
            f"{len(resultado['puladas'])} já importada(s)")


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
                             "sorteio pelo nome de cada uma, 1 em 10 para o teste)")
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

    arquivos = listar_arquivos(args.entradas)
    if not arquivos:
        parser.error("nenhuma imagem nas entradas")
    resultado = importar(args.saida, arquivos, args.lote, carregar_nomes(args.classes),
                         args.conjunto, args.regiao, args.lado_maximo, args.link)
    print(f"{resumo(args.lote, resultado)} em {args.saida.resolve()}")


if __name__ == "__main__":
    try:
        main()
    except ValueError as erro:
        sys.exit(f"Erro: {erro}")
