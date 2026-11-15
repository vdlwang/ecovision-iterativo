"""Testes do revisar.py, com o servidor numa thread e propostas sintéticas."""

import json
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest
import yaml
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import revisar  # noqa: E402
import saida as formato  # noqa: E402

CLASSES = [
    {"nome": "Garrafa", "prompt": "plastic bottle", "material": "plastic"},
    {"nome": "Lata", "prompt": "can", "material": "metal"},
]


def gravar_proposta(saida, nome, caixas, parametros=None):
    """caixas: [(classe, confianca)] ou [(classe, confianca, caixa em pixels de 40x20)]."""
    return formato.nova_proposta(saida, "falso", nome, [
        (c[0], c[1], tuple(v / d for v, d in zip(c[2] if len(c) > 2 else (4, 2, 20, 10),
                                                (40, 20, 40, 20))))
        for c in caixas], parametros or {}, versao="v1")


def montar(pasta, nomes_classes=("Garrafa", "Lata")):
    for nome in ("a.jpg", "b c.png", "d.jpg", "e.jpg", "f.jpg"):
        (pasta / "images").mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (40, 20)).save(pasta / "images" / nome)
    (pasta / "images" / "fora.jpg").write_bytes(b"")   # não registrada
    (pasta / "segredo.txt").write_text("não deve sair")
    formato.preparar(pasta, nomes_classes)
    formato.registrar(pasta, [(n, 40, 20) for n in ("a.jpg", "b c.png", "d.jpg", "e.jpg",
                                                    "f.jpg")],
                       "l1", {"conjunto": "treino"})
    gravar_proposta(pasta, "a.jpg", [("Lata", 0.9), ("Garrafa", 0.6)])
    gravar_proposta(pasta, "b c.png", [("Lata", 0.3)])
    gravar_proposta(pasta, "d.jpg", [])
    formato.revisar(pasta, "e.jpg", {"acao": "salvar", "caixas": [
        {"id": 1, "caixa": [0.4, 0.3, 0.6, 0.7]}]}, "t")
    formato.revisar(pasta, "f.jpg", {"acao": "descartar"}, "t")
    return pasta


@pytest.fixture
def saida(tmp_path):
    return montar(tmp_path)


@pytest.fixture
def servidor(saida):
    srv = revisar.criar_servidor(saida, CLASSES, porta=0)
    thread = threading.Thread(target=srv.serve_forever, args=(0.05,), daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def pedir(url):
    """(status, tipo, corpo) sem levantar exceção nos erros HTTP."""
    try:
        with urllib.request.urlopen(url) as r:
            return r.status, r.headers["Content-Type"], r.read()
    except urllib.error.HTTPError as erro:
        return erro.code, erro.headers["Content-Type"], erro.read()


def pedir_json(url):
    status, tipo, corpo = pedir(url)
    assert tipo.startswith("application/json")
    return status, json.loads(corpo)


def test_pagina(servidor):
    status, tipo, corpo = pedir(servidor + "/")
    assert status == 200 and tipo.startswith("text/html")
    assert b"/api/imagens" in corpo


def test_classes_com_material_e_atalho(tmp_path):
    # Fundo está no banco mas não no classes.yaml; o atalho segue a ordem do
    # classes.yaml, não o id
    srv = revisar.criar_servidor(montar(tmp_path, ("Fundo", "Lata", "Garrafa")), CLASSES, porta=0)
    threading.Thread(target=srv.serve_forever, args=(0.05,), daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}"
    resposta = pedir_json(url + "/api/classes")
    srv.shutdown()
    srv.server_close()
    assert resposta == (200, [
        {"id": 0, "nome": "Fundo", "material": None, "atalho": None},
        {"id": 1, "nome": "Lata", "material": "metal", "atalho": 2},
        {"id": 2, "nome": "Garrafa", "material": "plastic", "atalho": 1}])


def test_fila_pendentes_mais_incertas_antes(servidor):
    status, dados = pedir_json(servidor + "/api/imagens")
    assert status == 200
    assert [i["nome"] for i in dados["imagens"]] == ["d.jpg", "b c.png", "a.jpg"]
    a = dados["imagens"][2]
    assert a == {"nome": "a.jpg", "status": "pendente", "anotadores": ["falso"],
                 "n_caixas": {"falso": 2}, "confianca_min": 0.6, "tem_final": False}
    assert dados["anotadores"] == ["falso"]
    assert dados["contagem"] == {"pendente": 3, "revisada": 1, "descartada": 1}


def test_fila_filtro_e_ordem(servidor):
    _, dados = pedir_json(servidor + "/api/imagens?status=todas&ordem=nome")
    assert [i["nome"] for i in dados["imagens"]] == ["a.jpg", "b c.png", "d.jpg", "e.jpg",
                                                     "f.jpg"]
    _, dados = pedir_json(servidor + "/api/imagens?status=revisada")
    assert [(i["nome"], i["tem_final"], i["anotadores"]) for i in dados["imagens"]] == [
        ("e.jpg", True, [])]
    assert pedir_json(servidor + "/api/imagens?status=aprovada")[0] == 400
    assert pedir_json(servidor + "/api/imagens?ordem=data")[0] == 400


def test_detalhe_da_imagem(servidor, saida):
    status, dados = pedir_json(servidor + "/api/imagens/b%20c.png")
    assert status == 200
    assert dados == {
        "nome": "b c.png", "status": "pendente", "final": None, "invalidas": 0,
        "propostas": {"falso": [{"id": 1, "nome": "Lata", "conf": 0.3,
                                 "caixa": [0.1, 0.1, 0.5, 0.5], "indice": 0}]},
        "candidatas": {"falso": []},
        "propostas_ids": {"falso": formato.ler_proposta(saida, "falso", "b c.png")["id"]},
        "largura": 40, "altura": 20, "revisao": None}
    _, dados = pedir_json(servidor + "/api/imagens/e.jpg")
    assert dados["final"] == [{"id": 1, "nome": "Lata", "conf": None,
                               "caixa": [0.4, 0.3, 0.6, 0.7]}]


def test_imagem(servidor):
    status, tipo, corpo = pedir(servidor + "/images/b%20c.png")
    assert status == 200 and tipo == "image/png" and corpo.startswith(b"\x89PNG")


@pytest.mark.parametrize("rota", [
    "/images/fora.jpg", "/api/imagens/fora.jpg", "/images/..%2Fsegredo.txt",
    "/images/../segredo.txt", "/api/imagens/..%2Fdata.yaml", "/images/", "/nada"])
def test_404_fora_do_csv_e_fora_da_saida(servidor, rota):
    status, _, corpo = pedir(servidor + rota)
    assert status == 404, rota
    assert b"n\xc3\xa3o deve sair" not in corpo


def test_main_recusa_saida_sem_banco(tmp_path):
    (tmp_path / "data.yaml").write_text("names: {0: a}\n")
    with pytest.raises(ValueError, match="anotacoes.sqlite"):
        revisar.main([str(tmp_path)])


# --- PUT: salvar e descartar (fase 3) -----------------------------------------

def enviar(url, corpo, tipo="application/json", host=None):
    dados = corpo if isinstance(corpo, bytes) else json.dumps(corpo).encode()
    req = urllib.request.Request(url, data=dados, method="PUT", headers={"Content-Type": tipo})
    if host:
        req.add_unredirected_header("Host", host)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as erro:
        return erro.code, json.loads(erro.read())


def caixas_de(saida, nome, *trocas):
    """As propostas de 'falso' como a página as envia, com (índice, novo id) trocados."""
    dados = formato.ler_imagem(saida, nome, formato.nomes_classes(saida), ["falso"], None)
    caixas = [{"id": c["id"], "caixa": c["caixa"], "proposta": c["indice"]}
              for c in dados["propostas"]["falso"]]
    for k, novo in trocas:  # k: posição na lista das visíveis
        caixas[k]["id"] = novo
    return caixas


def test_salvar_grava_rotulo_registro_e_status(servidor, saida):
    caixas = caixas_de(saida, "a.jpg", (1, 1))  # a 2ª proposta (Garrafa) vira Lata
    del caixas[0]                                # a 1ª (Lata) é removida
    status, dados = enviar(servidor + "/api/imagens/a.jpg",
                           {"acao": "salvar", "base": "falso", "tempo_ativo_s": 7,
                            "caixas": caixas})
    assert status == 200, dados
    assert dados["status"] == "revisada"
    assert (saida / "labels" / "a.txt").read_text() == "1 0.300000 0.300000 0.400000 0.400000\n"
    revisao = dados["revisao"]
    assert revisao["acao"] == "salvar" and revisao["tempo_ativo_s"] == 7
    assert revisao["base"] == {"anotador": "falso", "versao": "v1", "classes": None,
                               "proposta_id": formato.ler_proposta(saida, "falso", "a.jpg")["id"],
                               "limiares": {"confianca": 0.0, "confianca_classe": 0.0}}
    assert revisao["caixas"] == [{"id": 1, "caixa": [0.1, 0.1, 0.5, 0.5], "proposta": 1,
                                  "desfecho": "classe_corrigida"}]
    assert revisao["removidas"] == [0]
    assert "a.jpg" in (saida / "revisadas.txt").read_text()
    # não está mais na fila de pendentes, e não pode ser editada de novo
    _, fila = pedir_json(servidor + "/api/imagens")
    assert "a.jpg" not in [i["nome"] for i in fila["imagens"]]
    assert enviar(servidor + "/api/imagens/a.jpg", {"acao": "descartar"})[0] == 409


def test_aceitar_como_esta_e_fundo(servidor, saida):
    status, dados = enviar(servidor + "/api/imagens/b%20c.png",
                           {"acao": "salvar", "base": "falso",
                            "caixas": caixas_de(saida, "b c.png")})
    assert status == 200
    assert [c["desfecho"] for c in dados["revisao"]["caixas"]] == ["aceita"]
    # Os mesmos .txt do --aceitar
    esperado = "".join(formato.linha_yolo(1, c) + "\n" for _, _, c in formato.caixas_normalizadas(
        formato.ler_proposta(saida, "falso", "b c.png")))
    assert (saida / "labels" / "b c.txt").read_text() == esperado
    # imagem sem caixas: salva como fundo, .txt vazio
    status, dados = enviar(servidor + "/api/imagens/d.jpg",
                           {"acao": "salvar", "base": "falso", "caixas": []})
    assert status == 200 and (saida / "labels" / "d.txt").read_text() == ""


def test_classe_escondida_abaixo_de_confianca_classe(servidor, saida):
    gravar_proposta(saida, "a.jpg", [("Lata", 0.9), ("Garrafa", 0.25)],
                    {"confianca": 0.2, "confianca_classe": 0.5})
    # A página recebe a caixa sem a classe do anotador, nem pelo nome
    status, tipo, corpo = pedir(servidor + "/api/imagens/a.jpg")
    dados = json.loads(corpo)
    assert dados["propostas"]["falso"][1] == {"id": None, "nome": None, "conf": 0.25,
                                              "caixa": [0.1, 0.1, 0.5, 0.5], "indice": 1}
    assert b"Garrafa" not in corpo
    caixas = caixas_de(saida, "a.jpg")
    status, erro = enviar(servidor + "/api/imagens/a.jpg",
                          {"acao": "salvar", "base": "falso", "caixas": caixas})
    assert status == 400 and "fora do data.yaml" in erro["erro"]
    caixas[1]["id"] = 0  # a mesma classe do anotador: ainda assim, atribuída
    status, dados = enviar(servidor + "/api/imagens/a.jpg",
                           {"acao": "salvar", "base": "falso", "caixas": caixas})
    assert status == 200, dados
    assert [c["desfecho"] for c in dados["revisao"]["caixas"]] == ["aceita", "classe_atribuida"]
    assert dados["revisao"]["base"]["limiares"] == {"confianca": 0.2, "confianca_classe": 0.5}


def test_caixa_de_candidata(servidor, saida):
    gravar_proposta(saida, "a.jpg",
                    [("Lata", 0.9), ("Garrafa", 0.12, [20, 10, 36, 18]), ("Lata", 0.08, [0, 0, 8, 8])],
                    {"confianca": 0.2})
    _, detalhe = pedir_json(servidor + "/api/imagens/a.jpg")
    assert [c["indice"] for c in detalhe["propostas"]["falso"]] == [0]
    assert detalhe["candidatas"]["falso"] == [
        {"indice": 1, "conf": 0.12, "caixa": [0.5, 0.5, 0.9, 0.9]},
        {"indice": 2, "conf": 0.08, "caixa": [0.0, 0.0, 0.2, 0.4]}]
    url = servidor + "/api/imagens/a.jpg"
    base = caixas_de(saida, "a.jpg")
    nova = {"id": 0, "caixa": [0.5, 0.5, 0.9, 0.9], "proposta": None, "origem": "candidata"}
    # origem desconhecida, candidata inexistente, origem em caixa de proposta, candidata
    # citada como proposta (não é visível)
    for caixa, trecho in ((dict(nova, origem="desenho"), "desconhecida"),
                          (dict(nova, caixa=[0.5, 0.5, 0.8, 0.9]), "candidatas"),
                          (dict(base[0], origem="candidata"), "não tem origem"),
                          (dict(nova, proposta=1, origem=None), "não existe")):
        status, erro = enviar(url, {"acao": "salvar", "base": "falso", "caixas": [caixa]})
        assert status == 400 and trecho in erro["erro"], erro
    status, dados = enviar(url, {"acao": "salvar", "base": "falso", "caixas": base + [nova]})
    assert status == 200, dados
    assert dados["revisao"]["caixas"][1] == {"id": 0, "caixa": [0.5, 0.5, 0.9, 0.9],
                                             "proposta": None, "desfecho": "adicionada",
                                             "origem": "candidata"}
    assert dados["revisao"]["removidas"] == []  # candidatas não contam como removidas
    assert (saida / "labels" / "a.txt").read_text().splitlines()[1] == \
        "0 0.700000 0.700000 0.400000 0.400000"


def test_descartar_apaga_o_rotulo(saida):
    (saida / "labels" / "a.txt").write_text("0 0.5 0.5 0.1 0.1\n")
    registro = formato.revisar(saida, "a.jpg", {"acao": "descartar", "base": "falso"}, "agora")
    assert not (saida / "labels" / "a.txt").exists()
    assert registro["removidas"] == [0, 1] and registro["caixas"] == []
    assert formato.ler_estado(saida)["a.jpg"]["status"] == "descartada"
    assert formato.ler_revisao(saida, "a.jpg")["acao"] == "descartar"


@pytest.mark.parametrize("corpo, trecho", [
    ({"acao": "apagar"}, "acao"),
    ({"acao": "salvar", "tempo_ativo_s": -1}, "tempo_ativo_s"),
    ({"acao": "salvar", "base": "outro"}, "não tem proposta"),
    ({"acao": "salvar", "base": "..", "caixas": []}, "não tem proposta"),
    ({"acao": "salvar", "caixas": [{"id": 5, "caixa": [0, 0, 1, 1]}]}, "classe 5"),
    ({"acao": "salvar", "caixas": [{"id": 0, "caixa": [0.5, 0, 0.2, 1]}]}, "invertidas"),
    ({"acao": "salvar", "caixas": [{"id": 0, "caixa": [0, 0, 1.2, 1]}]}, "fora de"),
    ({"acao": "salvar", "base": "falso",
      "caixas": [{"id": 0, "caixa": [0.1, 0.1, 0.5, 0.5], "proposta": 7}]}, "não existe"),
    ({"acao": "salvar", "base": "falso",
      "caixas": [{"id": 1, "caixa": [0.1, 0.1, 0.5, 0.6], "proposta": 0}]}, "decisão 12"),
    ({"acao": "salvar", "base": "falso",
      "caixas": [{"id": 1, "caixa": [0.1, 0.1, 0.5, 0.5], "proposta": 0},
                 {"id": 1, "caixa": [0.1, 0.1, 0.5, 0.5], "proposta": 0}]}, "duas vezes"),
])
def test_salvar_recusa_pedido_invalido_sem_gravar(servidor, saida, corpo, trecho):
    status, dados = enviar(servidor + "/api/imagens/a.jpg", corpo)
    assert status == 400 and trecho in dados["erro"], dados
    assert not (saida / "labels" / "a.txt").exists()
    assert formato.ler_revisao(saida, "a.jpg") is None
    assert formato.ler_estado(saida)["a.jpg"]["status"] == "pendente"


def test_put_protecoes(servidor):
    url = servidor + "/api/imagens/a.jpg"
    assert enviar(url, {"acao": "descartar"}, tipo="text/plain")[0] == 415
    assert enviar(url, b"nada")[0] == 400
    assert enviar(url, {"acao": "descartar"}, host="exemplo.com")[0] == 403
    assert enviar(servidor + "/api/imagens/fora.jpg", {"acao": "descartar"})[0] == 404
    assert enviar(servidor + "/api/classes", {"acao": "descartar"})[0] == 404


def test_put_com_proposta_vigente_e_com_proposta_antiga(servidor, saida):
    url = servidor + "/api/imagens/a.jpg"
    _, detalhe = pedir_json(url)
    vista = detalhe["propostas_ids"]["falso"]
    gravar_proposta(saida, "a.jpg", [("Garrafa", 0.9)])   # o anotador grava outra versão
    status, erro = enviar(url, {"acao": "salvar", "base": "falso", "proposta_id": vista,
                                "caixas": []})
    assert status == 409 and "recarregue" in erro["erro"]
    _, detalhe = pedir_json(url)
    status, dados = enviar(url, {"acao": "salvar", "base": "falso", "caixas": [],
                                 "proposta_id": detalhe["propostas_ids"]["falso"]})
    assert status == 200 and dados["revisao"]["base"]["proposta_id"] != vista
