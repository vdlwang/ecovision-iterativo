"""
Importa um lote de imagens para o armazenamento comum da anotação (OBJETIVO.md,
seção 6, tarefa T5).

Cada imagem é gravada uma vez em <saida>/images/<lote>_<nome> e registrada em
imagens.csv como pendente, com o lote e o conjunto (treino ou teste) dele. Todos
os anotadores (anotar.py) leem de lá; nenhum copia imagens.

    <saida>/images/<lote>_<nome>   cópia (ou link) da imagem
    <saida>/imagens.csv            nome, status, lote, conjunto
    <saida>/lotes.yaml             por lote: conjunto, região de interesse, data

A imagem muda o mínimo: só é regravada se o EXIF a gira (as caixas têm de valer
para a imagem girada em qualquer leitor) ou se passa de --lado-maximo; fora
isso, cópia byte a byte (recomprimir um JPEG perde qualidade). Sem normalizar
cor nem recortar: a base de treino tem de parecer com o que a câmera vê na
operação.

Conjunto: o lote inteiro vai para treino ou teste, nunca dividido (frames
seguidos são quase iguais). O sorteio é pelo hash do nome do lote, cerca de 1
lote em cada 5 para o teste (decisão 7), e é sempre o mesmo para o mesmo nome;
--conjunto força. Uma vez gravado, o conjunto de um lote não muda.

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
from datetime import datetime
from pathlib import Path

import yaml
from PIL import Image, ImageOps

import saida as formato
from anotar import DIR_SCRIPT, TAG_ORIENTACAO_EXIF, carregar_nomes, preparar_saida

CONJUNTOS = ("treino", "teste")
FRACAO_TESTE = 5  # 1 lote em cada 5 vai para o teste (decisão 7)
COLUNAS_LOTE = ["lote", "conjunto"]
LOTE_VALIDO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]*$")
QUALIDADE_JPEG = 95


def sortear_conjunto(lote):
    """'teste' para cerca de 1 lote em cada FRACAO_TESTE, sempre o mesmo para o mesmo nome."""
    valor = int.from_bytes(hashlib.sha256(lote.encode("utf-8")).digest()[:8], "big")
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
    é pulada. O conjunto e a região de um lote já existente não mudam; pedir
    outros é erro. Devolve {'importadas': [...], 'puladas': [...], 'conjunto': ...}.
    """
    saida = Path(saida)
    if not LOTE_VALIDO.match(lote):
        raise ValueError(f"nome de lote inválido: '{lote}' (letras, dígitos, '.' e '-'; "
                         "sem '_', que separa o lote do nome da imagem)")
    if conjunto is not None and conjunto not in CONJUNTOS:
        raise ValueError(f"conjunto deve ser um de {', '.join(CONJUNTOS)}")
    regiao = validar_regiao(regiao)

    preparar_saida(saida, nomes_classes)
    lotes = formato.ler_lotes(saida)
    if lote in lotes:
        existente = lotes[lote]
        if conjunto is not None and conjunto != existente["conjunto"]:
            raise ValueError(f"o lote {lote} já é de {existente['conjunto']}; o conjunto "
                             "de um lote não muda")
        if regiao is not None and regiao != existente.get("regiao"):
            raise ValueError(f"o lote {lote} já tem região {existente.get('regiao')}")
    else:
        lotes[lote] = {"conjunto": conjunto or sortear_conjunto(lote), "regiao": regiao,
                       "importado_em": agora or datetime.now().astimezone().isoformat(
                           timespec="seconds")}
    conjunto = lotes[lote]["conjunto"]

    colunas, linhas = formato.ler_estado(saida)
    colunas += [c for c in COLUNAS_LOTE if c not in colunas]
    nomes = [f"{lote}_{a.name}" for a in arquivos]
    repetidos = sorted({n for n in nomes if nomes.count(n) > 1})
    if repetidos:
        raise ValueError(f"nomes repetidos na entrada: {', '.join(repetidos)}")

    importadas, puladas = [], []
    for arquivo, nome in zip(arquivos, nomes):
        if nome in linhas:
            puladas.append(nome)
            continue
        formato.registrar_imagem(dict(linhas), nome)  # confere a colisão antes de gravar
        gravar_imagem(arquivo, saida / "images" / nome, lado_maximo, link)
        formato.registrar_imagem(linhas, nome)
        linhas[nome].update({"lote": lote, "conjunto": conjunto})
        importadas.append(nome)

    # lotes.yaml antes do imagens.csv: interrompido entre os dois, o lote existe
    # sem imagens, e importar de novo as registra
    formato.gravar_lotes(saida, lotes)
    formato.gravar_estado(saida, colunas, linhas)
    return {"importadas": importadas, "puladas": puladas, "conjunto": conjunto}


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Importa um lote de imagens para o armazenamento comum da anotação.")
    parser.add_argument("entradas", nargs="+", help="imagens ou pastas de imagens")
    parser.add_argument("-o", "--saida", type=Path, default=Path("anotacoes"),
                        help="diretório de saída (padrão: ./anotacoes)")
    parser.add_argument("--lote", required=True,
                        help="nome do lote de captura (letras, dígitos, '.' e '-')")
    parser.add_argument("--conjunto", choices=CONJUNTOS,
                        help="força o conjunto do lote (padrão: sorteio pelo nome, 1 em 5 "
                             "para o teste)")
    parser.add_argument("--regiao", type=float, nargs=4, metavar=("X1", "Y1", "X2", "Y2"),
                        help="região de interesse do lote, normalizada (0 a 1): os "
                             "anotadores descartam caixas com o centro fora dela")
    parser.add_argument("--lado-maximo", type=int,
                        help="reduz imagens com o lado maior acima disso (padrão: não reduz)")
    parser.add_argument("--link", action="store_true",
                        help="link em vez de cópia, quando a imagem não precisa ser regravada")
    parser.add_argument("--classes", type=Path, default=DIR_SCRIPT / "classes.yaml",
                        help="lista de classes, para o data.yaml (padrão: anotacao/classes.yaml)")
    args = parser.parse_args(argv)
    if args.lado_maximo is not None and args.lado_maximo < 32:
        parser.error("--lado-maximo pequeno demais")

    arquivos = listar_arquivos(args.entradas)
    if not arquivos:
        parser.error("nenhuma imagem nas entradas")
    resultado = importar(args.saida, arquivos, args.lote, carregar_nomes(args.classes),
                         args.conjunto, args.regiao, args.lado_maximo, args.link)
    print(f"Lote {args.lote} ({resultado['conjunto']}): {len(resultado['importadas'])} "
          f"imagem(ns) importada(s), {len(resultado['puladas'])} já importada(s) em "
          f"{args.saida.resolve()}")


if __name__ == "__main__":
    try:
        main()
    except ValueError as erro:
        sys.exit(f"Erro: {erro}")
