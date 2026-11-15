"""Testes do metricas.py: funções puras com registros sintéticos e um caso pelo banco."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import metricas  # noqa: E402
import saida as formato  # noqa: E402
import votar  # noqa: E402
from auxiliar import pedido  # noqa: E402

A = (0.1, 0.1, 0.3, 0.3)
B = (0.5, 0.5, 0.7, 0.7)
C = (0.8, 0.0, 0.9, 0.1)


def registro(nome, conjunto="treino", status="revisada", resultado="falhou", motivo="caixas",
             auditoria=False, propostas=(), acao="salvar", caixas=(), removidas=0, tempo=10.0,
             revisada=True):
    voto = None if resultado is None else {
        "resultado": resultado, "motivo": motivo if resultado == "falhou" else None,
        "auditoria": auditoria, "caixas": [],
        "propostas": [{"anotador": a, "limiar": 0.2, "caixas": list(c)} for a, c in propostas]}
    revisao = None if not revisada else {"acao": acao, "tempo_ativo_s": tempo,
                                         "caixas": list(caixas), "removidas": removidas}
    return {"nome": nome, "conjunto": conjunto, "status": status, "voto": voto,
            "revisao": revisao}


def aceita(classe, caixa):
    return (classe, caixa, "voto", "aceita")


def test_wilson():
    assert metricas.wilson(0, 0) is None
    p, lo, hi = metricas.wilson(9, 10)
    assert p == 0.9 and lo == pytest.approx(0.596, abs=1e-3) and hi == pytest.approx(0.982, abs=1e-3)
    assert metricas.wilson(10, 10)[2] == pytest.approx(1.0)


def test_voto_conta_aprovadas_motivos_teste_e_sem_voto():
    registros = [
        registro("a", resultado="aprovada", status="pendente", revisada=False),
        registro("b", resultado="aprovada", auditoria=True, status="pendente", revisada=False),
        registro("c", motivo="quantidade", status="pendente", revisada=False),
        registro("d", motivo="quantidade", status="pendente", revisada=False),
        registro("e", motivo="vazia", status="pendente", revisada=False),
        registro("t", conjunto="teste", resultado="uniao", status="pendente", revisada=False),
        registro("s", resultado=None, status="pendente", revisada=False),
    ]
    v = metricas.medir_voto(registros)
    assert v == {"treino_votadas": 5, "aprovadas": 2, "taxa_aprovacao": 0.4, "auditadas": 1,
                 "falhou": {"quantidade": 2, "vazia": 1}, "teste_unidas": 1, "sem_voto": 1}


def test_auditoria_correta_por_inteiro_e_destino_das_caixas():
    def auditada(nome, **kw):
        return registro(nome, resultado="aprovada", auditoria=True, **kw)
    registros = [
        auditada("ok", caixas=[aceita("Lata", A), aceita("Garrafa", B)]),
        auditada("troca", caixas=[aceita("Lata", A), ("Tampa", B, "voto", "classe_corrigida")]),
        auditada("sobra", caixas=[aceita("Lata", A)], removidas=1),
        auditada("falta", caixas=[aceita("Lata", A), ("Lata", C, "candidata", "adicionada")]),
        auditada("lixo", acao="descartar"),
        auditada("pendente", status="pendente", revisada=False),
        registro("aprovada fora da auditoria", resultado="aprovada",
                 caixas=[("Tampa", A, "voto", "classe_corrigida")]),
    ]
    a = metricas.medir_auditoria(registros)
    assert (a["auditadas"], a["revistas"], a["descartadas"], a["corretas"]) == (6, 5, 1, 1)
    assert a["fracao_correta"]["p"] == pytest.approx(0.2)
    assert a["caixas_consenso"] == {"aceita": 5, "classe_corrigida": 1, "removida": 1}
    assert a["objetos_perdidos"] == 1


def test_correcoes_e_tempo_por_grupo():
    registros = [
        registro("f1", caixas=[aceita("Lata", A), ("Tampa", B, "voto", "classe_atribuida"),
                               ("Lata", C, "proposta", "adicionada")], removidas=2, tempo=30),
        registro("f2", acao="descartar", tempo=4),
        registro("t1", conjunto="teste", resultado="uniao",
                 caixas=[("Lata", A, "proposta", "adicionada"),
                         ("Lata", B, "candidata", "adicionada")], tempo=20),
        registro("s", resultado=None, status="pendente", revisada=False),
    ]
    c = metricas.medir_correcoes(registros)
    assert list(c) == ["falhou", "teste"]
    assert c["falhou"] == {"salvas": 1, "descartadas": 1, "caixas": 3, "removidas": 2,
                           "desfechos": {"aceita": 1, "classe_corrigida": 0,
                                         "classe_atribuida": 1, "adicionada": 1},
                           "adicionadas": {"proposta": 1}}
    assert c["teste"]["adicionadas"] == {"candidata": 1, "proposta": 1}
    t = metricas.medir_tempo(registros)
    assert list(t) == ["falhou", "teste", "todas"]
    assert t["falhou"] == {"revisoes": 2, "mediana_s": 17, "media_s": 17, "por_objeto_s": 10}
    assert t["todas"]["por_objeto_s"] == pytest.approx(50 / 5)
    assert t["todas"]["mediana_s"] == 20


def test_anotadores_precisao_e_recall_sem_e_com_classe():
    verdade = [aceita("Lata", A), aceita("Garrafa", B)]
    registros = [registro("x", caixas=verdade, propostas=[
        # a: acha os dois, um com a classe errada, e uma caixa que sobra
        ("a", [("Lata", 0.9, A), ("Tampa", 0.8, B), ("Lata", 0.5, C)]),
        # b: só a lata; a garrafa está abaixo do limiar de leitura (0,2)
        ("b", [("Lata", 0.9, A), ("Garrafa", 0.1, B)])]),
        registro("descartada", acao="descartar", propostas=[("a", [("Lata", 0.9, A)])])]
    m = metricas.medir_anotadores(registros)
    a, b = m["treino"]["a"], m["treino"]["b"]
    assert (a["imagens"], a["previstas"], a["objetos"]) == (1, 3, 2)
    assert a["localizacao"] == {"acertos": 2, "precisao": pytest.approx(2 / 3), "recall": 1.0}
    assert a["classe"] == {"acertos": 1, "precisao": pytest.approx(1 / 3), "recall": 0.5}
    assert b["localizacao"] == {"acertos": 1, "precisao": 1.0, "recall": 0.5}


def test_casar_e_guloso_e_um_para_um():
    previstas = [("Lata", A), ("Lata", A)]
    assert metricas.casar(previstas, [("Lata", A)], 0.5, True) == 1
    assert metricas.casar([("Lata", A)], [("Garrafa", A)], 0.5, True) == 0
    assert metricas.casar([("Lata", A)], [("Garrafa", A)], 0.5, False) == 1


def test_de_ponta_a_ponta_pelo_banco(tmp_path, capsys):
    saida = tmp_path
    formato.preparar(saida, ["Garrafa", "Lata"])
    formato.registrar(saida, [("l1_x.jpg", 100, 50, "treino"), ("l1_y.jpg", 100, 50, "treino"),
                              ("l1_t.jpg", 100, 50, "teste")], "l1", {})
    limiares = {"confianca": 0.2, "confianca_classe": 0.35}
    lata, garrafa = ("Lata", 0.9, A), ("Garrafa", 0.8, B)
    for anotador, caixas_y in (("a", [lata, garrafa]), ("b", [lata])):
        formato.nova_proposta(saida, anotador, "l1_x.jpg", [lata], limiares)
        formato.nova_proposta(saida, anotador, "l1_y.jpg", caixas_y, limiares)
        formato.nova_proposta(saida, anotador, "l1_t.jpg", [lata], limiares)
    votar.votar(saida, ["a", "b"], auditoria=1)
    # x: aprovada e auditada, aceita como está; y: falhou, o revisor tira a garrafa
    voto_x = formato.ler_voto(saida, "l1_x.jpg")
    formato.revisar(saida, "l1_x.jpg", pedido(saida, "l1_x.jpg", tempo=12, caixas=[
        {"id": 1, "caixa": c["caixa"], "origem": "voto", "indice": k}
        for k, c in enumerate(voto_x["caixas"])]), "t")
    voto_y = formato.ler_voto(saida, "l1_y.jpg")
    k = next(k for k, c in enumerate(voto_y["caixas"]) if c["id"] == 1)
    formato.revisar(saida, "l1_y.jpg", pedido(saida, "l1_y.jpg", tempo=20, caixas=[
        {"id": 1, "caixa": voto_y["caixas"][k]["caixa"], "origem": "voto", "indice": k}]), "t")

    json_saida = tmp_path / "m.json"
    metricas.main([str(saida), "--json", str(json_saida)])
    texto = capsys.readouterr().out
    assert "1 aprovada(s) (50%; 1 na auditoria cega)" in texto
    assert "1 de 1 revista(s): 1 correta(s) por inteiro" in texto
    m = json.loads(json_saida.read_text())
    assert m["voto"]["falhou"] == {"quantidade": 1}
    assert m["correcoes"]["falhou"]["removidas"] == 1
    assert m["tempo"]["todas"]["revisoes"] == 2
    # a achou a garrafa que o revisor removeu: precisão 2/3 no treino; b, 2/2
    assert m["anotadores"]["treino"]["a"]["localizacao"]["precisao"] == pytest.approx(2 / 3)
    assert m["anotadores"]["treino"]["b"]["localizacao"]["precisao"] == 1.0
    assert "teste" not in m["anotadores"]   # a de teste ainda não foi revisada
    # revisada do zero, a de teste não "remove" as caixas da união, que não viu
    base = formato.voto_para_revisao(saida, "l1_t.jpg", formato.nomes_classes(saida))
    c = base["candidatas"][0]
    registro = formato.revisar(saida, "l1_t.jpg", pedido(saida, "l1_t.jpg", caixas=[
        {"id": 1, "caixa": c["caixa"], "origem": c["origem"], "anotador": c["anotador"],
         "indice": c["indice"]}]), "t")
    assert registro["removidas"] == []
    m = metricas.medir(formato.ler_registros(saida))
    assert m["correcoes"]["teste"]["removidas"] == 0
    assert m["anotadores"]["teste"]["a"]["localizacao"]["recall"] == 1.0


def test_main_recusa_saida_sem_banco(tmp_path):
    with pytest.raises(ValueError, match="não tem banco"):
        metricas.main([str(tmp_path)])


def cenario_com_auditoria():
    return [
        registro("aud", resultado="aprovada", auditoria=True, caixas=[aceita("Lata", A)], tempo=8),
        registro("rep", motivo="quantidade", caixas=[aceita("Lata", A)], tempo=20),
        registro("apr", resultado="aprovada", status="pendente", revisada=False),
        registro("t", conjunto="teste", resultado="uniao", status="pendente", revisada=False),
    ]


def test_modo_cego_mostra_so_o_que_a_pagina_mostra():
    registros = cenario_com_auditoria()
    completo = metricas.medir(registros)
    assert set(completo["correcoes"]) == {"falhou", "auditoria"}
    assert completo["voto"]["auditadas"] == 1
    cego = metricas.medir(registros, cega=True)
    assert cego["cega"] and "auditoria" not in cego
    # como na fila: a auditada está entre as "a revisar", sem motivos nem taxa
    assert cego["voto"] == {"treino_votadas": 3, "aprovadas": 1, "a_revisar": 2,
                            "teste_unidas": 1, "sem_voto": 0}
    assert list(cego["correcoes"]) == ["falhou"] and cego["correcoes"]["falhou"]["salvas"] == 2
    assert cego["tempo"]["falhou"]["revisoes"] == 2
    assert "auditoria" not in json.dumps(cego).lower()


def test_avisos_de_inconsistencia_e_de_leitura():
    registros = cenario_com_auditoria() + [
        registro("sem_rev", status="revisada", revisada=False),
        registro("pend_rev", status="pendente"),
        registro("tempo0", tempo=0),
        registro("troca", conjunto="teste", resultado="aprovada"),
    ]
    avisos = metricas.medir(registros)["avisos"]
    texto = "\n".join(avisos)
    assert "revisada ou descartada sem revisão registrada: sem_rev" in texto
    assert "pendente com revisão registrada: pend_rev" in texto
    assert "conjunto e resultado do voto não batem" in texto and "troca" in texto
    assert "tempo ativo zero" in texto and "tempo0" in texto
    assert "Auditoria: 1 de 1" in texto
    # "troca" é de teste e foi salva: há teste revisado, sem o aviso de base de teste vazia
    assert "Nenhuma imagem de teste revisada" not in texto
    cegos = metricas.medir(registros, cega=True)["avisos"]
    assert not any("uditoria" in a for a in cegos)
    assert "Nenhuma imagem de teste revisada" in "\n".join(
        metricas.medir(cenario_com_auditoria())["avisos"])
