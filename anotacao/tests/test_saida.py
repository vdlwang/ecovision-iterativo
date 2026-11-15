"""Testes do estado da anotação no SQLite (saida.py)."""

import os
import sqlite3
import stat
import sys
import threading
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import saida as formato  # noqa: E402
from auxiliar import do_voto, pedido, votar_imagens  # noqa: E402

CLASSES = [
    {"nome": "Garrafa", "prompt": "plastic bottle", "material": "plastic"},
    {"nome": "Lata", "prompt": "can", "material": "metal"},
]
LIMIARES = {"confianca": 0.2, "confianca_classe": 0.35}


def criar(saida, nomes=("Garrafa", "Lata"), imagens=("a.jpg",)):
    formato.preparar(saida, nomes)
    formato.registrar(saida, [(n, 100, 50, "treino") for n in imagens], "l1", {})
    return saida


def test_preparar_cria_banco_classes_e_arquivos(tmp_path):
    formato.preparar(tmp_path, ["Garrafa", "Tampa", "Lata"])
    assert formato.existe(tmp_path)
    assert formato.nomes_classes(tmp_path) == {0: "Garrafa", 1: "Tampa", 2: "Lata"}
    dados = yaml.safe_load((tmp_path / "data.yaml").read_text(encoding="utf-8"))
    assert dados == {"train": "treino.txt", "val": "teste.txt",
                     "names": {0: "Garrafa", 1: "Tampa", 2: "Lata"}}
    for lista in ("treino.txt", "teste.txt", "revisadas.txt"):
        assert (tmp_path / lista).read_text() == ""
    assert formato.ler_estado(tmp_path) == {} and formato.ler_lotes(tmp_path) == {}
    with sqlite3.connect(formato.caminho_banco(tmp_path)) as con:
        assert con.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_preparar_acrescenta_no_fim_ou_refaz_sem_ids_gravados(tmp_path):
    criar(tmp_path, ["Garrafa", "Lata"], ["a.jpg", "b.jpg", "c.jpg"])
    formato.preparar(tmp_path, ["Garrafa", "Lata", "Tampa"])   # acréscimo no fim
    assert formato.nomes_classes(tmp_path) == {0: "Garrafa", 1: "Lata", 2: "Tampa"}
    formato.preparar(tmp_path, ["Lata", "Garrafa"])            # sem ids gravados: refeito
    assert formato.nomes_classes(tmp_path) == {0: "Lata", 1: "Garrafa"}
    # Voto sem caixas, fundo e descarte não guardam ids; a candidata vira caixa
    # só na revisão
    candidata = ("Lata", 0.1, (0.1, 0.1, 0.5, 0.5))
    votar_imagens(tmp_path, ["a.jpg", "b.jpg"], [candidata])
    formato.revisar(tmp_path, "a.jpg", pedido(tmp_path, "a.jpg"), "t")
    formato.preparar(tmp_path, ["Garrafa", "Lata"])
    formato.revisar(tmp_path, "b.jpg", pedido(tmp_path, "b.jpg", caixas=[
        {"id": 1, "caixa": [0.1, 0.1, 0.5, 0.5], "origem": "candidata", "anotador": "v1",
         "indice": 0}]), "t")
    with pytest.raises(ValueError, match="outras classes"):
        formato.preparar(tmp_path, ["Lata", "Garrafa"])
    formato.preparar(tmp_path, ["Garrafa", "Lata", "Tampa"])   # acréscimo continua valendo


def test_preparar_recusa_reordenar_com_voto_de_classe(tmp_path):
    criar(tmp_path)
    votar_imagens(tmp_path, ["a.jpg"], [("Lata", 0.9, (0.1, 0.1, 0.5, 0.5))])
    with pytest.raises(ValueError, match="votos com caixas de classe"):
        formato.preparar(tmp_path, ["Lata", "Garrafa"])


def test_preparar_recusa_formatos_anteriores(tmp_path):
    (tmp_path / "csv").mkdir()
    (tmp_path / "csv" / "imagens.csv").write_text("nome,status\n")
    with pytest.raises(ValueError, match="anterior ao SQLite"):
        formato.preparar(tmp_path / "csv", ["Garrafa"])
    (tmp_path / "antigo" / "labels").mkdir(parents=True)
    (tmp_path / "antigo" / "labels" / "foto.txt").write_text("0 0.5 0.5 0.1 0.1\n")
    with pytest.raises(ValueError, match="formato antigo"):
        formato.preparar(tmp_path / "antigo", ["Garrafa"])


def test_banco_de_outra_versao_e_recusado(tmp_path):
    criar(tmp_path)
    with sqlite3.connect(formato.caminho_banco(tmp_path)) as con:
        con.execute("PRAGMA user_version = 99")
    with pytest.raises(ValueError, match="versão 99"):
        formato.ler_estado(tmp_path)


def test_registrar_lote_estado_e_colisoes(tmp_path):
    formato.preparar(tmp_path, ["Garrafa"])
    lote = {"regiao": [0, 0.1, 1, 0.9], "importado_em": "ontem"}
    assert formato.registrar(tmp_path, [("l1_a.jpg", 40, 20, "teste"),
                                        ("l1_b.png", 40, 20, "treino")],
                             "l1", lote, agora="hoje") == ["l1_a.jpg", "l1_b.png"]
    # já registrada: pulada, com o status e o conjunto mantidos
    assert formato.registrar(tmp_path, [("l1_a.jpg", 40, 20, "treino")], "l1", lote) == []
    assert formato.ler_lotes(tmp_path) == {"l1": lote}
    estado = formato.ler_estado(tmp_path)
    assert list(estado) == ["l1_a.jpg", "l1_b.png"]
    assert estado["l1_a.jpg"] == {"nome": "l1_a.jpg", "status": "pendente", "lote": "l1",
                                  "conjunto": "teste", "voto": None, "motivo": None,
                                  "largura": 40, "altura": 20}
    assert estado["l1_b.png"]["conjunto"] == "treino"   # o conjunto é de cada imagem
    with pytest.raises(ValueError, match="colide"):
        formato.registrar(tmp_path, [("l1_a.png", 40, 20, "treino")], "l1")
    with pytest.raises(ValueError, match="conjunto"):
        formato.registrar(tmp_path, [("l1_c.png", 40, 20, "validacao")], "l1")
    # imagem só entra num lote existente (criado pelo importar.py)
    with pytest.raises(ValueError, match="lote 'l9' não existe"):
        formato.registrar(tmp_path, [("l9_a.jpg", 40, 20, "treino")], "l9")
    assert "l9_a.jpg" not in formato.ler_estado(tmp_path)
    with pytest.raises(ValueError, match="colide"):
        formato.conferir_colisoes({}, ["x.jpg", "x.png"])
    formato.conferir_colisoes({"x.jpg": {}}, ["x.jpg"])  # a mesma: passa


def test_proposta_versionada_e_vigente(tmp_path):
    criar(tmp_path, imagens=("a.jpg", "b.jpg"))
    deteccoes = [("Lata", 0.876543, (0.123457, 0.2, 0.654321, 0.9)),
                 ("Garrafa", 0.4, (0.0, 0.0, 1.0, 1.0))]
    execucao = formato.nova_execucao(tmp_path, "falso", "tipo-falso", "v1", LIMIARES,
                                     formato.hash_classes(CLASSES), "t1")
    p1 = formato.gravar_proposta(tmp_path, execucao, "a.jpg", deteccoes, "t1")
    formato.gravar_proposta(tmp_path, execucao, "b.jpg", [], "t1")
    lida = formato.ler_proposta(tmp_path, "falso", "a.jpg")
    assert lida == {"id": p1, "anotador": "falso", "tipo": "tipo-falso", "versao": "v1",
                    "parametros": LIMIARES, "classes": formato.hash_classes(CLASSES),
                    "imagem": "a.jpg", "data": "t1",
                    "caixas": [("Lata", 0.8765, (0.123457, 0.2, 0.654321, 0.9)),
                               ("Garrafa", 0.4, (0.0, 0.0, 1.0, 1.0))]}
    # Anotar de novo cria outra versão; a anterior continua lida pelo id
    p2 = formato.nova_proposta(tmp_path, "falso", "a.jpg", [], versao="v2")
    assert formato.ler_proposta(tmp_path, "falso", "a.jpg")["id"] == p2
    assert formato.ler_proposta(tmp_path, "falso", "a.jpg", p1)["versao"] == "v1"
    assert formato.ler_proposta(tmp_path, "falso", "b.jpg", p1) is None   # é de outra imagem
    assert formato.ler_proposta(tmp_path, "outro", "a.jpg") is None
    atuais = formato.propostas_atuais(tmp_path, "falso")
    assert {n: p["versao"] for n, p in atuais.items()} == {"a.jpg": "v2", "b.jpg": "v1"}
    assert formato.imagens_com_proposta(tmp_path, "falso") == {"a.jpg", "b.jpg"}
    formato.nova_proposta(tmp_path, "outro", "b.jpg", [])
    assert formato.anotadores(tmp_path) == ["falso", "outro"]
    with pytest.raises(ValueError, match="não registrada"):
        formato.nova_proposta(tmp_path, "falso", "z.jpg", [])


def test_caixa_invalida_nao_entra_no_banco(tmp_path):
    criar(tmp_path)
    with pytest.raises(sqlite3.IntegrityError):
        formato.nova_proposta(tmp_path, "falso", "a.jpg", [("Lata", 0.9, (0.5, 0.1, 0.4, 0.2))])
    with pytest.raises(sqlite3.IntegrityError):
        formato.nova_proposta(tmp_path, "falso", "a.jpg", [("Lata", 1.5, (0.1, 0.1, 0.4, 0.2))])
    # a transação inteira volta: nenhuma proposta gravada
    assert formato.ler_proposta(tmp_path, "falso", "a.jpg") is None


def test_separar_aplica_os_limiares_da_proposta():
    proposta = {"parametros": LIMIARES, "caixas": [
        ("Lata", 0.9, (0.1, 0.2, 0.5, 0.6)), ("Garrafa", 0.3, (0.6, 0.2, 0.9, 0.6)),
        ("Lata", 0.1, (0.0, 0.0, 0.2, 0.2))]}
    visiveis, candidatas = formato.separar(proposta)
    assert list(visiveis) == [0, 1]
    assert visiveis[0][0] == "Lata" and visiveis[0][3] is True
    assert visiveis[1][0] == "Garrafa" and visiveis[1][3] is False  # classe escondida
    assert candidatas == [(2, 0.1, (0.0, 0.0, 0.2, 0.2))]
    # Sem limiares gravados: tudo visível, com classe
    proposta["parametros"] = {}
    visiveis, candidatas = formato.separar(proposta)
    assert list(visiveis) == [0, 1, 2] and not candidatas
    assert all(v[3] for v in visiveis.values())


def test_revisao_guarda_todas_as_sessoes_e_o_vigente_e_a_ultima(tmp_path):
    criar(tmp_path)
    votar_imagens(tmp_path, ["a.jpg"], [("Lata", 0.9, (0.1, 0.2, 0.5, 0.6))])
    formato.revisar(tmp_path, "a.jpg", pedido(tmp_path, "a.jpg", "descartar"), "t1")
    # reabrir é a fase 5; aqui, direto no banco, para conferir o histórico
    with formato.abrir(tmp_path) as con, formato.transacao(con):
        con.execute("UPDATE imagens SET status = 'pendente'")
    registro = formato.revisar(tmp_path, "a.jpg", pedido(tmp_path, "a.jpg"), "t2")
    assert registro["acao"] == "salvar" and registro["removidas"] == [0]
    with formato.abrir(tmp_path) as con:
        assert [r[0] for r in con.execute("SELECT acao FROM revisoes ORDER BY id")] == \
            ["descartar", "salvar"]


def test_revisao_exige_o_voto_vigente(tmp_path):
    criar(tmp_path)
    with pytest.raises(formato.RevisaoInvalida, match="não foi votada") as erro:
        formato.revisar(tmp_path, "a.jpg", {"acao": "salvar", "voto_id": 1}, "t")
    assert erro.value.status == 409
    antigo = votar_imagens(tmp_path, ["a.jpg"])["a.jpg"]
    novo = votar_imagens(tmp_path, ["a.jpg"])["a.jpg"]   # propostas novas: outro voto
    assert novo != antigo
    with pytest.raises(formato.RevisaoInvalida, match="não é mais o vigente") as erro:
        formato.revisar(tmp_path, "a.jpg", {"acao": "salvar", "voto_id": antigo}, "t")
    assert erro.value.status == 409
    with pytest.raises(formato.RevisaoInvalida, match="voto_id"):
        formato.revisar(tmp_path, "a.jpg", {"acao": "salvar"}, "t")
    assert formato.ler_estado(tmp_path)["a.jpg"]["status"] == "pendente"


def test_exportar_refaz_os_arquivos_do_banco(tmp_path):
    criar(tmp_path, imagens=("a.jpg", "b.jpg"))
    votar_imagens(tmp_path, ["a.jpg"], [("Garrafa", 0.9, (0.1, 0.1, 0.5, 0.5))])
    formato.revisar(tmp_path, "a.jpg", pedido(tmp_path, "a.jpg", caixas=[
        do_voto(tmp_path, "a.jpg", 0, 1)]), "t")
    texto = (tmp_path / "labels" / "a.txt").read_text()
    (tmp_path / "labels" / "a.txt").unlink()
    (tmp_path / "labels" / "b.txt").write_text("0 0.5 0.5 0.1 0.1\n")   # b não está revisada
    (tmp_path / "data.yaml").unlink()
    (tmp_path / "revisadas.txt").unlink()
    formato.exportar(tmp_path)
    assert (tmp_path / "labels" / "a.txt").read_text() == texto
    assert not (tmp_path / "labels" / "b.txt").exists()
    assert yaml.safe_load((tmp_path / "data.yaml").read_text())["names"] == {0: "Garrafa",
                                                                             1: "Lata"}
    assert (tmp_path / "revisadas.txt").read_text() == "./images/a.jpg\n"


def test_copia_seguranca(tmp_path):
    criar(tmp_path)
    formato.copia_seguranca(tmp_path)
    with sqlite3.connect(tmp_path / (formato.BANCO + ".bak")) as con:
        assert con.execute("SELECT nome FROM imagens").fetchall() == [("a.jpg",)]


def test_escritas_concorrentes_nao_se_perdem(tmp_path):
    """Duas threads gravando ao mesmo tempo (o servidor e o anotar.py): nada se perde."""
    nomes = [f"{i}.jpg" for i in range(40)]
    criar(tmp_path, imagens=nomes)
    votos = votar_imagens(tmp_path, nomes)
    erros = []

    def anotar():
        try:
            for nome in nomes:
                formato.nova_proposta(tmp_path, "falso", nome, [("Lata", 0.9, (0.1, 0.1, 0.2, 0.2))])
        except Exception as erro:  # pragma: no cover - aparece na asserção
            erros.append(erro)

    def revisar():
        try:
            for nome in nomes[::2]:
                formato.revisar(tmp_path, nome, {"acao": "descartar",
                                                 "voto_id": votos[nome]}, "t")
        except Exception as erro:  # pragma: no cover
            erros.append(erro)

    threads = [threading.Thread(target=anotar), threading.Thread(target=revisar)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not erros
    assert formato.imagens_com_proposta(tmp_path, "falso") == set(nomes)
    estado = formato.ler_estado(tmp_path)
    assert sum(l["status"] == "descartada" for l in estado.values()) == 20


def test_ler_rotulos_e_nomes_de_pasta_yolo_sem_banco(tmp_path):
    (tmp_path / "data.yaml").write_text("names: [a, b]\n")
    assert formato.nomes_classes(tmp_path) == {0: "a", 1: "b"}
    (tmp_path / "x.txt").write_text("0 0.5 0.5 0.2 0.4\nlixo\n")
    caixas, invalidas = formato.ler_rotulos(tmp_path / "x.txt")
    assert invalidas == 1 and caixas[0][0] == 0
    assert caixas[0][1] == pytest.approx((0.4, 0.3, 0.6, 0.7))


def test_hash_classes_muda_com_a_ordem():
    assert formato.hash_classes(CLASSES) != formato.hash_classes(CLASSES[::-1])


def test_gravar_atomico_usa_o_modo_de_um_open_comum(tmp_path):
    formato.gravar_atomico(tmp_path / "a.txt", "x")
    (tmp_path / "b.txt").write_text("x")
    assert stat.S_IMODE(os.stat(tmp_path / "a.txt").st_mode) == \
        stat.S_IMODE(os.stat(tmp_path / "b.txt").st_mode)
    assert not [p for p in tmp_path.iterdir() if p.name.startswith(".")]  # sem temporários
