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
import votar  # noqa: E402
from auxiliar import do_voto  # noqa: E402

CLASSES = [
    {"nome": "Garrafa", "prompt": "plastic bottle", "material": "plastic"},
    {"nome": "Lata", "prompt": "can", "material": "metal"},
]
DUPLA = ["falso", "outro"]
LIMIARES = {"confianca": 0.2, "confianca_classe": 0.5}
CAIXA = (4, 2, 20, 10)      # em pixels de 40x20: (0.1, 0.1, 0.5, 0.5)
OUTRA = (24, 2, 36, 18)     # (0.6, 0.1, 0.9, 0.9)


def gravar_proposta(saida, nome, caixas, anotador="falso", parametros=LIMIARES):
    """caixas: [(classe, confianca)] ou [(classe, confianca, caixa em pixels de 40x20)]."""
    return formato.nova_proposta(saida, anotador, nome, [
        (c[0], c[1], tuple(v / d for v, d in zip(c[2] if len(c) > 2 else CAIXA,
                                                (40, 20, 40, 20))))
        for c in caixas], parametros, versao="v1")


def montar(pasta, nomes_classes=("Garrafa", "Lata")):
    """
    a.jpg: falhou (quantidade), consenso na lata, a garrafa só de falso;
    b c.png: aprovada; d.jpg: falhou (vazia); e.jpg: revisada; f.jpg:
    descartada; g.jpg: sem voto (só falso); t.jpg: teste, união sem classe.
    """
    nomes = ("a.jpg", "b c.png", "d.jpg", "e.jpg", "f.jpg", "g.jpg", "t.jpg")
    (pasta / "images").mkdir(parents=True, exist_ok=True)
    for nome in nomes:
        Image.new("RGB", (40, 20)).save(pasta / "images" / nome)
    (pasta / "images" / "fora.jpg").write_bytes(b"")   # não registrada
    (pasta / "segredo.txt").write_text("não deve sair")
    formato.preparar(pasta, nomes_classes)
    formato.registrar(pasta, [(n, 40, 20, "treino") for n in nomes[:-1]], "l1", {})
    formato.registrar(pasta, [("t.jpg", 40, 20, "teste")], "t1", {})
    gravar_proposta(pasta, "a.jpg", [("Lata", 0.9), ("Garrafa", 0.6, OUTRA)])
    gravar_proposta(pasta, "a.jpg", [("Lata", 0.9)], "outro")
    for anotador in DUPLA:
        gravar_proposta(pasta, "b c.png", [("Lata", 0.3)], anotador)
        gravar_proposta(pasta, "d.jpg", [], anotador)
        gravar_proposta(pasta, "e.jpg", [("Lata", 0.9)], anotador)
        gravar_proposta(pasta, "f.jpg", [], anotador)
        gravar_proposta(pasta, "t.jpg", [("Lata", 0.9)], anotador)
    gravar_proposta(pasta, "g.jpg", [("Lata", 0.9)])
    votar.votar(pasta, DUPLA)
    formato.revisar(pasta, "e.jpg", {"acao": "salvar", "voto_id": voto(pasta, "e.jpg"),
                                     "caixas": [do_voto(pasta, "e.jpg", 0, 1)]}, "t")
    formato.revisar(pasta, "f.jpg", {"acao": "descartar", "voto_id": voto(pasta, "f.jpg")}, "t")
    return pasta


def voto(saida, nome):
    return formato.ler_voto(saida, nome)["id"]


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


def test_fila_a_revisar_mais_incertas_antes(servidor):
    status, dados = pedir_json(servidor + "/api/imagens")
    assert status == 200
    # as que falharam no voto e as de teste; sem proposta visível antes
    assert [i["nome"] for i in dados["imagens"]] == ["d.jpg", "a.jpg", "t.jpg"]
    assert dados["imagens"][1] == {
        "nome": "a.jpg", "status": "pendente", "situacao": "a_revisar", "voto": "falhou",
        "motivo": None, "anotadores": DUPLA, "n_caixas": {"falso": 2, "outro": 1},
        "confianca_min": 0.6, "tem_final": False}
    # teste: na fila, sem confiança nem anotadores
    assert (dados["imagens"][2]["confianca_min"], dados["imagens"][2]["anotadores"]) == (None, [])
    assert dados["anotadores"] == DUPLA
    assert dados["contagem"] == {"a_revisar": 3, "aprovada": 1, "sem_voto": 1, "revisada": 1,
                                 "descartada": 1}


def test_fila_filtro_e_ordem(servidor):
    _, dados = pedir_json(servidor + "/api/imagens?status=todas&ordem=nome")
    assert [i["nome"] for i in dados["imagens"]] == ["a.jpg", "b c.png", "d.jpg", "e.jpg",
                                                     "f.jpg", "g.jpg", "t.jpg"]
    for situacao, nomes in (("revisada", ["e.jpg"]), ("aprovada", ["b c.png"]),
                            ("sem_voto", ["g.jpg"]), ("descartada", ["f.jpg"])):
        _, dados = pedir_json(servidor + f"/api/imagens?status={situacao}")
        assert [i["nome"] for i in dados["imagens"]] == nomes
    assert pedir_json(servidor + "/api/imagens?status=pendente")[0] == 400
    assert pedir_json(servidor + "/api/imagens?ordem=data")[0] == 400


def test_detalhe_traz_o_voto_como_base(servidor, saida):
    status, dados = pedir_json(servidor + "/api/imagens/a.jpg")
    assert status == 200
    assert (dados["situacao"], dados["conjunto"], dados["revisao"]) == ("a_revisar", "treino", None)
    assert dados["voto"] == {
        "id": voto(saida, "a.jpg"), "resultado": "falhou", "motivo": None,
        "conjunto": "treino",
        "caixas": [{"id": 1, "nome": "Lata", "conf": 0.9, "caixa": [0.1, 0.1, 0.5, 0.5],
                    "indice": 0, "anotadores": DUPLA, "sugestoes": []},
                   # a garrafa, só de falso: conflito, com a classe dele como sugestão
                   {"id": None, "nome": None, "conf": 0.6, "caixa": [0.6, 0.1, 0.9, 0.9],
                    "indice": 1, "anotadores": ["falso"], "sugestoes": [
                        {"id": 0, "nome": "Garrafa",
                         "anotadores": [{"anotador": "falso", "conf": 0.6}]}]}],
        "candidatas": []}
    _, dados = pedir_json(servidor + "/api/imagens/e.jpg")
    assert dados["final"] == [{"id": 1, "nome": "Lata", "conf": None,
                               "caixa": [0.1, 0.1, 0.5, 0.5]}]
    _, dados = pedir_json(servidor + "/api/imagens/g.jpg")
    assert dados["voto"] is None and dados["situacao"] == "sem_voto"


def test_detalhe_do_teste_sem_classe_nem_confianca(servidor):
    status, tipo, corpo = pedir(servidor + "/api/imagens/t.jpg")
    dados = json.loads(corpo)
    assert dados["voto"]["resultado"] == "uniao" and dados["voto"]["conjunto"] == "teste"
    # sem pré-anotação: nenhuma caixa; a do objeto vem pelo clique, das candidatas
    assert dados["voto"]["caixas"] == []
    assert dados["voto"]["candidatas"] == [{"anotador": "falso", "indice": 0,
                                            "origem": "proposta", "conf": 0.9,
                                            "caixa": [0.1, 0.1, 0.5, 0.5]}]
    # nem pelas camadas de propostas
    assert dados["propostas"] == {} and b"Lata" not in corpo


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


# --- PUT: salvar e descartar -----------------------------------------------------

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


def test_salvar_grava_rotulo_registro_e_status(servidor, saida):
    caixas = [do_voto(saida, "a.jpg", 0, 0),                  # a lata do voto vira garrafa
              do_voto(saida, "a.jpg", 1, 0)]                    # o conflito recebe a classe
    status, dados = enviar(servidor + "/api/imagens/a.jpg",
                           {"acao": "salvar", "voto_id": voto(saida, "a.jpg"),
                            "tempo_ativo_s": 7, "caixas": caixas})
    assert status == 200, dados
    assert dados["status"] == "revisada" and dados["situacao"] == "revisada"
    assert (saida / "labels" / "a.txt").read_text() == (
        "0 0.300000 0.300000 0.400000 0.400000\n0 0.750000 0.500000 0.300000 0.800000\n")
    revisao = dados["revisao"]
    assert revisao["acao"] == "salvar" and revisao["tempo_ativo_s"] == 7
    assert revisao["voto_id"] == voto(saida, "a.jpg") and revisao["removidas"] == []
    assert [(c["origem"], c["anotador"], c["indice"], c["desfecho"])
            for c in revisao["caixas"]] == [("voto", None, 0, "classe_corrigida"),
                                            ("voto", None, 1, "classe_atribuida")]
    assert "a.jpg" in (saida / "revisadas.txt").read_text()
    # não está mais na fila, e não pode ser editada de novo
    _, fila = pedir_json(servidor + "/api/imagens")
    assert "a.jpg" not in [i["nome"] for i in fila["imagens"]]
    assert enviar(servidor + "/api/imagens/a.jpg",
                  {"acao": "descartar", "voto_id": voto(saida, "a.jpg")})[0] == 409


def test_aprovada_aceita_como_esta_e_fundo(servidor, saida):
    status, dados = enviar(servidor + "/api/imagens/b%20c.png",
                           {"acao": "salvar", "voto_id": voto(saida, "b c.png"),
                            "caixas": [do_voto(saida, "b c.png", 0, 1)]})
    assert status == 200
    assert [c["desfecho"] for c in dados["revisao"]["caixas"]] == ["aceita"]
    assert (saida / "labels" / "b c.txt").read_text() == \
        formato.linha_yolo(1, (0.1, 0.1, 0.5, 0.5)) + "\n"
    # voto vazio: salva como fundo, .txt vazio
    status, dados = enviar(servidor + "/api/imagens/d.jpg",
                           {"acao": "salvar", "voto_id": voto(saida, "d.jpg"), "caixas": []})
    assert status == 200 and (saida / "labels" / "d.txt").read_text() == ""


def test_teste_recebe_a_caixa_pelo_clique_e_a_classe_do_revisor(servidor, saida):
    url, corpo = servidor + "/api/imagens/t.jpg", {"acao": "salvar",
                                                   "voto_id": voto(saida, "t.jpg")}
    status, erro = enviar(url, dict(corpo, caixas=[do_voto(saida, "t.jpg", 0, 1)]))
    assert status == 400 and "sem pré-anotação" in erro["erro"]
    caixa = {"id": 1, "caixa": [0.1, 0.1, 0.5, 0.5], "origem": "proposta",
             "anotador": "falso", "indice": 0}
    status, dados = enviar(url, dict(corpo, caixas=[caixa]))
    assert status == 200, dados
    assert [c["desfecho"] for c in dados["revisao"]["caixas"]] == ["adicionada"]
    assert (saida / "teste.txt").read_text() == "./images/t.jpg\n"


def test_conflito_sugere_mesmo_abaixo_de_confianca_classe(servidor, saida):
    gravar_proposta(saida, "a.jpg", [("Lata", 0.9), ("Garrafa", 0.25, OUTRA)])
    votar.votar(saida, DUPLA)     # proposta nova de falso: a imagem é votada de novo
    _, dados = pedir_json(servidor + "/api/imagens/a.jpg")
    conflito = dados["voto"]["caixas"][1]
    assert (conflito["id"], conflito["sugestoes"]) == (None, [
        {"id": 0, "nome": "Garrafa", "anotadores": [{"anotador": "falso", "conf": 0.25}]}])
    caixa = {"id": None, "caixa": [0.6, 0.1, 0.9, 0.9], "origem": "voto", "indice": 1}
    url, corpo = servidor + "/api/imagens/a.jpg", {"acao": "salvar",
                                                   "voto_id": dados["voto"]["id"]}
    status, erro = enviar(url, dict(corpo, caixas=[caixa]))
    assert status == 400 and "fora do data.yaml" in erro["erro"]
    status, dados = enviar(url, dict(corpo, caixas=[dict(caixa, id=0)]))
    assert status == 200, dados
    assert dados["revisao"]["caixas"][0]["desfecho"] == "classe_atribuida"
    assert dados["revisao"]["removidas"] == [0]


def test_candidatas_de_todos_os_anotadores_sem_repetidas(servidor, saida):
    gravar_proposta(saida, "a.jpg", [("Lata", 0.9), ("Garrafa", 0.12, (20, 10, 36, 18)),
                                     ("Lata", 0.08, (0, 0, 8, 8))])
    gravar_proposta(saida, "a.jpg", [("Lata", 0.9), ("Garrafa", 0.11, (20, 10, 36, 18)),
                                     ("Lata", 0.05, (30, 0, 38, 8))], "outro")
    votar.votar(saida, DUPLA)
    _, detalhe = pedir_json(servidor + "/api/imagens/a.jpg")
    assert detalhe["voto"]["resultado"] == "aprovada"
    # a garrafa de outro é quase igual à de falso, mais confiante: fica só a de falso
    assert [(c["anotador"], c["indice"], c["conf"]) for c in detalhe["voto"]["candidatas"]] == \
        [("falso", 1, 0.12), ("falso", 2, 0.08), ("outro", 2, 0.05)]
    nova = {"id": 0, "caixa": [0.5, 0.5, 0.9, 0.9], "origem": "candidata", "anotador": "falso",
            "indice": 1}
    url = servidor + "/api/imagens/a.jpg"
    corpo = {"acao": "salvar", "voto_id": detalhe["voto"]["id"]}
    for caixa, trecho in ((dict(nova, origem="proposta"), "não é visível"),
                          (dict(nova, caixa=[0.5, 0.5, 0.8, 0.9]), "decisão 12"),
                          (dict(nova, indice=9), "não tem a caixa 9")):
        status, erro = enviar(url, dict(corpo, caixas=[caixa]))
        assert status == 400 and trecho in erro["erro"], erro
    status, dados = enviar(url, dict(corpo, caixas=[do_voto(saida, "a.jpg", 0, 1), nova]))
    assert status == 200, dados
    assert dados["revisao"]["caixas"][1] == {"id": 0, "caixa": [0.5, 0.5, 0.9, 0.9],
                                             "origem": "candidata", "indice": 1,
                                             "anotador": "falso", "desfecho": "adicionada"}
    assert (saida / "labels" / "a.txt").read_text().splitlines()[1] == \
        "0 0.700000 0.700000 0.400000 0.400000"


def test_descartar_apaga_o_rotulo(saida):
    (saida / "labels" / "a.txt").write_text("0 0.5 0.5 0.1 0.1\n")
    registro = formato.revisar(saida, "a.jpg", {"acao": "descartar",
                                                "voto_id": voto(saida, "a.jpg")}, "agora")
    assert not (saida / "labels" / "a.txt").exists()
    assert registro["removidas"] == [0, 1] and registro["caixas"] == []
    assert formato.ler_estado(saida)["a.jpg"]["status"] == "descartada"
    assert formato.ler_revisao(saida, "a.jpg")["acao"] == "descartar"


@pytest.mark.parametrize("corpo, trecho", [
    ({"acao": "apagar"}, "acao"),
    ({"acao": "salvar", "tempo_ativo_s": -1}, "tempo_ativo_s"),
    ({"acao": "salvar", "voto_id": None}, "voto_id"),
    ({"acao": "salvar", "caixas": [{"id": 5, "caixa": [0, 0, 1, 1], "origem": "voto",
                                    "indice": 0}]}, "classe 5"),
    ({"acao": "salvar", "caixas": [{"id": 0, "caixa": [0.5, 0, 0.2, 1], "origem": "voto",
                                    "indice": 0}]}, "invertidas"),
    ({"acao": "salvar", "caixas": [{"id": 0, "caixa": [0, 0, 1.2, 1], "origem": "voto",
                                    "indice": 0}]}, "fora de"),
    ({"acao": "salvar", "caixas": [{"id": 0, "caixa": [0.1, 0.1, 0.5, 0.5]}]}, "inválida"),
    ({"acao": "salvar", "caixas": [{"id": 0, "caixa": [0.1, 0.1, 0.5, 0.5], "origem": "voto",
                                    "indice": 7}]}, "não tem a caixa 7"),
    ({"acao": "salvar", "caixas": [{"id": 1, "caixa": [0.1, 0.1, 0.5, 0.6], "origem": "voto",
                                    "indice": 0}]}, "decisão 12"),
    ({"acao": "salvar", "caixas": [{"id": 1, "caixa": [0.1, 0.1, 0.5, 0.5], "origem": "voto",
                                    "indice": 0}] * 2}, "duas vezes"),
    ({"acao": "salvar", "caixas": [{"id": 1, "caixa": [0.1, 0.1, 0.5, 0.5], "origem": "proposta",
                                    "anotador": "nenhum", "indice": 0}]}, "não usou proposta"),
])
def test_salvar_recusa_pedido_invalido_sem_gravar(servidor, saida, corpo, trecho):
    corpo = {"voto_id": voto(saida, "a.jpg"), **corpo}
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


def test_put_sem_voto_e_com_voto_antigo(servidor, saida):
    status, erro = enviar(servidor + "/api/imagens/g.jpg", {"acao": "descartar", "voto_id": 1})
    assert status == 409 and "votar.py" in erro["erro"]
    url = servidor + "/api/imagens/a.jpg"
    _, detalhe = pedir_json(url)
    visto = detalhe["voto"]["id"]
    gravar_proposta(saida, "a.jpg", [("Garrafa", 0.9)])   # o anotador grava outra versão
    votar.votar(saida, DUPLA)                              # e a imagem é votada de novo
    status, erro = enviar(url, {"acao": "salvar", "voto_id": visto, "caixas": []})
    assert status == 409 and "recarregue" in erro["erro"]
    _, detalhe = pedir_json(url)
    status, dados = enviar(url, {"acao": "salvar", "caixas": [],
                                 "voto_id": detalhe["voto"]["id"]})
    assert status == 200 and dados["revisao"]["voto_id"] != visto


def test_auditada_aparece_como_reprovada(tmp_path):
    saida = montar(tmp_path)
    # b c.png foi aprovada; vota de novo com toda aprovada na auditoria
    votar.votar(saida, DUPLA, revotar=True, auditoria=1)
    assert formato.ler_estado(saida)["b c.png"]["auditoria"] is True
    fila = revisar.montar_fila(saida, "a_revisar")
    item = next(i for i in fila["imagens"] if i["nome"] == "b c.png")
    assert (item["situacao"], item["voto"], item["motivo"], item["tem_final"]) == (
        "a_revisar", "falhou", None, False)
    assert all(i["motivo"] is None for i in fila["imagens"])
    assert "b c.png" not in [i["nome"] for i in revisar.montar_fila(saida, "aprovada")["imagens"]]
    dados = revisar.detalhar(saida, "b%20c.png")
    assert dados["final"] is None and dados["situacao"] == "a_revisar"
    assert (dados["voto"]["resultado"], dados["voto"]["motivo"]) == ("falhou", None)
    # o rótulo de consenso continua em labels/ e no treino até a revisão
    assert (saida / "labels" / "b c.txt").exists()


def test_api_de_metricas_cega_por_padrao(tmp_path):
    saida = montar(tmp_path)
    votar.votar(saida, DUPLA, revotar=True, auditoria=1)   # b c.png, aprovada, vira auditada
    srv = revisar.criar_servidor(saida, CLASSES, porta=0)
    thread = threading.Thread(target=srv.serve_forever, args=(0.05,), daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{srv.server_address[1]}/api/metricas"
        status, cega = pedir_json(base)
        assert status == 200 and cega["cega"] and "auditoria" not in cega
        # e.jpg, aprovada e revisada antes, conta; b c.png, auditada, está entre as a revisar
        assert "auditadas" not in cega["voto"] and cega["voto"]["aprovadas"] == 1
        status, completa = pedir_json(base + "?auditoria=1")
        assert status == 200 and not completa["cega"]
        assert completa["auditoria"]["auditadas"] == 1 and completa["voto"]["auditadas"] == 1
    finally:
        srv.shutdown()
        srv.server_close()
