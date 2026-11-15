"""Ajudas dos testes: toda revisão parte de um voto, então as imagens são votadas antes."""

import saida as formato
import votar

LIMIARES = {"confianca": 0.2, "confianca_classe": 0.35}
DUPLA = ("v1", "v2")


def votar_imagens(saida, nomes, caixas=(), anotadores=DUPLA, parametros=LIMIARES):
    """
    Grava a mesma proposta (caixas: [(classe, confianca, caixa)]) de cada
    anotador em cada imagem e vota; devolve {nome: id do voto vigente}.
    """
    for nome in nomes:
        for anotador in anotadores:
            formato.nova_proposta(saida, anotador, nome, list(caixas), parametros)
    votar.votar(saida, list(anotadores))
    return {n: formato.ler_voto(saida, n)["id"] for n in nomes}


def pedido(saida, nome, acao="salvar", caixas=(), tempo=0):
    """Pedido de revisão sobre o voto vigente da imagem, como a página envia."""
    return {"acao": acao, "voto_id": formato.ler_voto(saida, nome)["id"],
            "caixas": list(caixas), "tempo_ativo_s": tempo}


def do_voto(saida, nome, indice, id_classe):
    """Caixa final que é a caixa indice do voto vigente, com a classe dada."""
    caixa = formato.ler_voto(saida, nome)["caixas"][indice]["caixa"]
    return {"id": id_classe, "caixa": caixa, "origem": "voto", "indice": indice}
