"""
Pipeline de anotação (OBJETIVO.md, seção 6, tarefa T14): importa um lote
(opcional), anota as imagens pendentes com cada anotador de anotadores.yaml,
um de cada vez, e vota. Nas imagens de treino, o voto NooN estrito; nas de
teste, a união sem classe (votar.py), que fica no banco: a revisão do teste
é sem pré-anotação.

    python anotacao/pipeline.py -o anotacoes fotos/ --lote 2026-11-15a
    python anotacao/pipeline.py -o anotacoes          # retoma: anota o que falta e vota

Retomável: a unidade de trabalho é (imagem, anotador). Cada proposta é
gravada numa transação própria, e o anotar.py pula as imagens que já têm
proposta do anotador; o voto pula as já votadas com as mesmas propostas.
Interrompida, a pipeline continua de onde parou com o mesmo comando (a
importação pula as imagens já importadas).

A configuração de todos os anotadores é conferida antes de importar ou
carregar qualquer modelo, para um erro no terceiro não aparecer depois de
horas de GPU. A votação grava a configuração usada.
"""

import argparse
import gc
import re
import sys
from pathlib import Path

import yaml

import anotar
import importar
import saida as formato
import votar

DIR_SCRIPT = Path(__file__).resolve().parent
CONFIG_PADRAO = DIR_SCRIPT / "anotadores.yaml"
NOME_VALIDO = re.compile(r"[a-z0-9][a-z0-9._-]*")
GRUPO_DETECCAO = "detecção"   # título do grupo de opções comuns no anotar.py


def opcoes_permitidas(tipo):
    """
    Opções do anotar.py (sem o '--') que o anotadores.yaml aceita para o tipo:
    as de detecção, comuns, e as do grupo do próprio tipo.
    """
    parser = anotar.criar_parser()
    permitidas = set()
    for grupo in parser._action_groups:
        if grupo.title in (GRUPO_DETECCAO, tipo):
            for acao in grupo._group_actions:
                permitidas.update(o[2:] for o in acao.option_strings if o.startswith("--"))
    return permitidas


def carregar_config(caminho):
    """
    Lê e confere o anotadores.yaml: {'anotadores': [{nome, tipo, opcoes}],
    'voto': {'iou', 'auditoria'}}, com os padrões preenchidos. Não confere os valores das
    opções; isso é com o anotar.py (argv_anotador e ler_argumentos).
    """
    with open(caminho, encoding="utf-8") as f:
        dados = yaml.safe_load(f) or {}
    if not isinstance(dados, dict):
        raise ValueError(f"{caminho}: esperado um mapa com 'anotadores'")
    fora = set(dados) - {"anotadores", "voto"}
    if fora:
        raise ValueError(f"{caminho}: chaves desconhecidas: {', '.join(sorted(fora))}")
    lista = dados.get("anotadores")
    if not isinstance(lista, list) or len(lista) < 2:
        raise ValueError(f"{caminho}: 'anotadores' precisa de ao menos dois")
    anotadores, nomes = [], set()
    for i, a in enumerate(lista):
        if not isinstance(a, dict):
            raise ValueError(f"{caminho}: anotador {i} não é um mapa")
        fora = set(a) - {"nome", "tipo", "opcoes"}
        if fora:
            raise ValueError(f"{caminho}: anotador {i} com chaves desconhecidas: "
                             f"{', '.join(sorted(fora))}")
        tipo = a.get("tipo")
        if tipo not in anotar.ANOTADORES:
            raise ValueError(f"{caminho}: anotador {i} com tipo {tipo!r} (use "
                             f"{', '.join(sorted(anotar.ANOTADORES))})")
        nome = a.get("nome", tipo)
        if not isinstance(nome, str) or not NOME_VALIDO.fullmatch(nome):
            raise ValueError(f"{caminho}: anotador {i} com nome {nome!r} (minúsculas, "
                             "dígitos, '.', '_' e '-')")
        if nome in nomes:
            raise ValueError(f"{caminho}: anotador '{nome}' repetido")
        nomes.add(nome)
        opcoes = a.get("opcoes") or {}
        if not isinstance(opcoes, dict):
            raise ValueError(f"{caminho}: 'opcoes' de '{nome}' não é um mapa")
        invalidas = sorted(set(opcoes) - opcoes_permitidas(tipo))
        if invalidas:
            raise ValueError(f"{caminho}: opções que '{nome}' ({tipo}) não aceita: "
                             f"{', '.join(invalidas)}")
        for chave, valor in opcoes.items():
            if isinstance(valor, bool) or not isinstance(valor, (int, float, str)):
                raise ValueError(f"{caminho}: opção '{chave}' de '{nome}' tem de ser número "
                                 "ou texto")
        anotadores.append({"nome": nome, "tipo": tipo, "opcoes": dict(opcoes)})
    voto = dados.get("voto") or {}
    if not isinstance(voto, dict) or set(voto) - {"iou", "auditoria"}:
        raise ValueError(f"{caminho}: 'voto' só aceita 'iou' e 'auditoria'")
    iou = voto.get("iou", votar.IOU_VOTO)
    if isinstance(iou, bool) or not isinstance(iou, (int, float)) or not 0 < iou <= 1:
        raise ValueError(f"{caminho}: voto.iou entre 0 e 1")
    auditoria = voto.get("auditoria", votar.AUDITORIA)
    if (isinstance(auditoria, bool) or not isinstance(auditoria, (int, float))
            or not 0 <= auditoria <= 1):
        raise ValueError(f"{caminho}: voto.auditoria entre 0 e 1")
    return {"anotadores": anotadores,
            "voto": {"iou": float(iou), "auditoria": float(auditoria)}}


def argv_anotador(anotador, saida, classes, dispositivo=None, previa=False):
    """A linha de comando do anotar.py para um anotador da configuração."""
    argv = ["-o", str(saida), "--anotador", anotador["tipo"], "--nome", anotador["nome"],
            "--classes", str(classes)]
    if dispositivo:
        argv += ["--dispositivo", dispositivo]
    if previa:
        argv.append("--previa")
    for chave, valor in anotador["opcoes"].items():
        argv += [f"--{chave}", str(valor)]
    return argv


def conferir_argumentos(config, argvs):
    """Passa cada linha de comando pelo anotar.py sem rodar; erro com o nome do anotador."""
    for anotador, argv in zip(config["anotadores"], argvs):
        try:
            anotar.ler_argumentos(argv)
        except SystemExit:   # o argparse já escreveu o motivo
            raise ValueError(f"opções inválidas para o anotador '{anotador['nome']}'") from None


def liberar_memoria():
    """Solta o modelo do anotador anterior antes de carregar o próximo (GTX 1650)."""
    gc.collect()
    torch = sys.modules.get("torch")
    if torch is not None and torch.cuda.is_available():
        torch.cuda.empty_cache()


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Importa um lote (opcional), anota com os anotadores de anotadores.yaml "
                    "e vota.")
    parser.add_argument("entradas", nargs="*",
                        help="imagens ou pastas a importar como --lote (sem elas, só anota e "
                             "vota o que já foi importado)")
    parser.add_argument("-o", "--saida", type=Path, default=Path("anotacoes"),
                        help="diretório de saída (padrão: ./anotacoes)")
    parser.add_argument("--config", type=Path, default=CONFIG_PADRAO,
                        help="anotadores e voto (padrão: anotacao/anotadores.yaml)")
    parser.add_argument("--classes", type=Path, default=DIR_SCRIPT / "classes.yaml",
                        help="lista de classes (padrão: anotacao/classes.yaml)")
    parser.add_argument("--dispositivo", help="cuda ou cpu, para todos os anotadores "
                                              "(padrão: cuda se houver)")
    parser.add_argument("--previa", action="store_true",
                        help="grava também previa/<anotador>/<nome>.jpg")
    grupo = parser.add_argument_group("importação", "como no importar.py; só com entradas")
    grupo.add_argument("--lote", help="nome do lote de captura")
    grupo.add_argument("--conjunto", choices=importar.CONJUNTOS,
                       help="força o conjunto de todas as imagens (padrão: sorteio por "
                            "imagem, 1 em 10 para o teste)")
    grupo.add_argument("--regiao", type=float, nargs=4, metavar=("X1", "Y1", "X2", "Y2"),
                       help="região de interesse do lote, normalizada")
    grupo.add_argument("--lado-maximo", type=int,
                       help="reduz imagens com o lado maior acima disso")
    grupo.add_argument("--link", action="store_true", help="link em vez de cópia")
    args = parser.parse_args(argv)
    importacao = [args.lote, args.conjunto, args.regiao, args.lado_maximo]
    if args.entradas and not args.lote:
        parser.error("entradas a importar precisam de --lote")
    if not args.entradas and (any(v is not None for v in importacao) or args.link):
        parser.error("as opções de importação só valem com entradas")
    if args.lado_maximo is not None and args.lado_maximo < 32:
        parser.error("--lado-maximo pequeno demais")

    # Tudo conferido antes de mexer na saída ou carregar modelo
    config = carregar_config(args.config)
    argvs = [argv_anotador(a, args.saida, args.classes, args.dispositivo, args.previa)
             for a in config["anotadores"]]
    conferir_argumentos(config, argvs)
    nomes_classes = anotar.carregar_nomes(args.classes)
    anotar.carregar_classes(args.classes)
    arquivos = importar.listar_arquivos(args.entradas) if args.entradas else []
    if args.entradas and not arquivos:
        parser.error("nenhuma imagem nas entradas")
    if not args.entradas and not formato.existe(args.saida):
        parser.error(f"{args.saida} não tem imagens importadas: passe entradas e --lote")

    if arquivos:
        r = importar.importar(args.saida, arquivos, args.lote, nomes_classes, args.conjunto,
                              args.regiao, args.lado_maximo, args.link)
        print(importar.resumo(args.lote, r))

    nomes = [a["nome"] for a in config["anotadores"]]
    for i, (nome, argv_a) in enumerate(zip(nomes, argvs), 1):
        print(f"\n== Anotador {i}/{len(nomes)}: {nome} ==")
        anotar.main(argv_a)
        liberar_memoria()

    print("\n== Voto ==")
    r = votar.votar(args.saida, nomes, limiar_iou=config["voto"]["iou"], configuracao=config,
                    auditoria=config["voto"]["auditoria"])
    votar.imprimir_resumo(args.saida, nomes, r)


if __name__ == "__main__":
    try:
        main()
    except ValueError as erro:
        sys.exit(f"Erro: {erro}")
