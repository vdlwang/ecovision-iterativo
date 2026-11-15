"""Testes do voto (votar.py e saida.votar), com propostas sintéticas."""

import sqlite3
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import saida as formato  # noqa: E402
import votar  # noqa: E402
from auxiliar import pedido  # noqa: E402

NOMES = ["Garrafa", "Lata", "Tampa"]
LIMIARES = {"confianca": 0.2, "confianca_classe": 0.35}
TRIO = ["a", "b", "c"]
GARRAFA = ("Garrafa", 0.9, (0.1, 0.1, 0.3, 0.3))
LATA = ("Lata", 0.8, (0.5, 0.5, 0.7, 0.7))


def perto(caixa, k, conf=None):
    classe, c, (x1, y1, x2, y2) = caixa
    return (classe, c if conf is None else conf, (x1 + k, y1 + k, x2 + k, y2 + k))


def criar(saida, lotes={"l1": "treino"}, por_lote=("x.jpg",)):
    formato.preparar(saida, NOMES)
    for lote, conjunto in lotes.items():
        formato.registrar(saida, [(f"{lote}_{n}", 100, 50, conjunto) for n in por_lote], lote,
                          {"regiao": None})
    return saida


def propor(saida, nome, por_anotador, parametros=LIMIARES):
    """por_anotador: {anotador: caixas}; uma proposta de cada."""
    return {a: formato.nova_proposta(saida, a, nome, caixas, parametros)
            for a, caixas in por_anotador.items()}


def concordam(saida, nome):
    return propor(saida, nome, {"a": [GARRAFA, LATA], "b": [perto(LATA, 0.01), perto(GARRAFA, 0.01)],
                                "c": [perto(GARRAFA, 0.02), perto(LATA, 0.02)]})


def linhas(saida, arquivo):
    return (saida / arquivo).read_text(encoding="utf-8").splitlines()


def test_votar_3oo3_estrito():
    a = (0, 0.9, (0.1, 0.1, 0.3, 0.3))
    b = (1, 0.8, (0.5, 0.5, 0.7, 0.7))
    perto = lambda d, k: (d[0], d[1] - 0.1, tuple(v + k for v in d[2]))  # noqa: E731
    # três concordam: consenso com a mediana das coordenadas e a menor confiança
    motivo, consenso = votar.voto_estrito([[a, b], [perto(b, 0.01), perto(a, 0.01)],
                                          [perto(a, 0.02), perto(b, 0.02)]])
    assert motivo is None
    assert consenso[0][0] == 0 and consenso[0][1] == pytest.approx(0.8)
    assert consenso[0][2] == pytest.approx((0.11, 0.11, 0.31, 0.31))
    # um anotador acha um objeto a menos
    assert votar.voto_estrito([[a, b], [a, b], [a]])[0] == "quantidade"
    # mesma quantidade, classe diferente
    assert votar.voto_estrito([[a], [a], [(1, 0.9, a[2])]])[0] == "caixas"
    # ninguém acha nada
    assert votar.voto_estrito([[], [], []]) == ("vazia", [])
    # b e c casam com a, mas não entre si (IoU entre eles < 0,5)
    esq = (0, 0.9, (0.0, 0.0, 0.3, 0.2))
    dir_ = (0, 0.9, (0.08, 0.0, 0.38, 0.2))
    meio = (0, 0.9, (0.05, 0.0, 0.35, 0.2))
    assert votar.voto_estrito([[meio], [esq], [dir_]])[0] is None
    longe = (0, 0.9, (0.12, 0.0, 0.42, 0.2))
    assert anotar_iou(meio, longe) >= 0.5 and anotar_iou(esq, longe) < 0.5
    assert votar.voto_estrito([[meio], [esq], [longe]])[0] == "caixas"


def anotar_iou(a, b):
    return votar.iou(a[2], b[2])


def test_aprovada_grava_consenso_rotulo_e_treino(tmp_path):
    saida = criar(tmp_path)
    ids = concordam(saida, "l1_x.jpg")
    r = votar.votar(saida, TRIO, agora="t")
    assert r == {"aprovadas": ["l1_x.jpg"], "falhou": {}, "uniao": [], "incompletas": 0,
                 "ja_votadas": 0}
    estado = formato.ler_estado(saida)["l1_x.jpg"]
    assert (estado["status"], estado["voto"], estado["motivo"]) == ("pendente", "aprovada", None)
    # consenso: a mediana das coordenadas, a menor confiança, na ordem do primeiro
    rotulo = linhas(saida, "labels/l1_x.txt")
    assert [l.split()[0] for l in rotulo] == ["0", "1"]
    assert rotulo[0] == formato.linha_yolo(0, (0.11, 0.11, 0.31, 0.31))
    assert linhas(saida, "treino.txt") == ["./images/l1_x.jpg"]
    assert linhas(saida, "teste.txt") == [] and linhas(saida, "revisadas.txt") == []
    dados = yaml.safe_load((saida / "data.yaml").read_text(encoding="utf-8"))
    assert (dados["train"], dados["val"]) == ("treino.txt", "teste.txt")
    voto = formato.ler_voto(saida, "l1_x.jpg")
    assert voto["anotadores"] == TRIO and voto["data"] == "t"
    assert voto["parametros"] == {"iou": 0.5, "limiares": {"a": None, "b": None, "c": None}}
    assert [(p["anotador"], p["id"], p["limiar"]) for p in voto["propostas"]] == \
        [(a, ids[a], 0.2) for a in TRIO]
    assert [c["id"] for c in voto["caixas"]] == [0, 1]
    assert voto["caixas"][0]["conf"] == pytest.approx(0.9)
    # cada caixa de consenso guarda de quais caixas das propostas veio
    assert voto["caixas"][0]["membros"] == [{"anotador": "a", "indice": 0},
                                            {"anotador": "b", "indice": 1},
                                            {"anotador": "c", "indice": 0}]


def test_falhou_fica_pendente_sem_rotulo(tmp_path):
    saida = criar(tmp_path, por_lote=("x.jpg", "y.jpg", "z.jpg"))
    propor(saida, "l1_x.jpg", {"a": [GARRAFA, LATA], "b": [GARRAFA, LATA], "c": [GARRAFA]})
    propor(saida, "l1_y.jpg", {"a": [GARRAFA], "b": [GARRAFA], "c": [("Lata", *GARRAFA[1:])]})
    propor(saida, "l1_z.jpg", {"a": [], "b": [], "c": []})
    r = votar.votar(saida, TRIO)
    assert r["falhou"] == {"l1_x.jpg": "quantidade", "l1_y.jpg": "caixas", "l1_z.jpg": "vazia"}
    assert {n: (e["status"], e["voto"], e["motivo"])
            for n, e in formato.ler_estado(saida).items()} == {
        "l1_x.jpg": ("pendente", "falhou", "quantidade"),
        "l1_y.jpg": ("pendente", "falhou", "caixas"),
        "l1_z.jpg": ("pendente", "falhou", "vazia")}
    assert not list((saida / "labels").glob("*.txt"))
    assert linhas(saida, "treino.txt") == []
    # a que falhou guarda uma caixa por objeto: consenso (a garrafa dos três)
    # ou conflito, sem classe (a lata que c não achou; a classe em disputa em y)
    assert [c["id"] for c in formato.ler_voto(saida, "l1_x.jpg")["caixas"]] == [0, None]
    assert [c["id"] for c in formato.ler_voto(saida, "l1_y.jpg")["caixas"]] == [None]
    assert formato.ler_voto(saida, "l1_z.jpg")["caixas"] == []


def test_so_pendentes_com_proposta_de_todos_e_teste_unido(tmp_path):
    saida = criar(tmp_path, {"l1": "treino", "t1": "teste"}, ("x.jpg", "y.jpg", "z.jpg"))
    for nome in ("l1_x.jpg", "l1_y.jpg", "l1_z.jpg", "t1_x.jpg"):
        concordam(saida, nome)
    votar.votar(saida, TRIO)
    formato.revisar(saida, "l1_z.jpg", pedido(saida, "l1_z.jpg", "descartar"), "t")
    formato.nova_proposta(saida, "a", "l1_y.jpg", [GARRAFA], LIMIARES)  # nova vigente de a
    r = votar.votar(saida, TRIO)
    assert r["falhou"] == {"l1_y.jpg": "quantidade"}   # a vigente de a tem uma caixa só
    assert r["ja_votadas"] == 2 and r["incompletas"] == 2   # l1_x, t1_x; t1_y, t1_z
    assert formato.ler_estado(saida)["l1_z.jpg"]["status"] == "descartada"
    # teste: união sem classe, nunca aprovada nem rotulada
    estado = formato.ler_estado(saida)["t1_x.jpg"]
    assert (estado["voto"], estado["motivo"]) == ("uniao", None)
    assert not (saida / "labels/t1_x.txt").exists()
    # sem proposta de um dos anotadores, a imagem espera
    propor(saida, "t1_y.jpg", {"a": [GARRAFA], "b": [GARRAFA]})
    assert votar.votar(saida, TRIO)["incompletas"] == 2


def test_uniao_funde_as_sobrepostas_sem_classe(tmp_path):
    saida = criar(tmp_path, {"t1": "teste"})
    tampa = ("Tampa", 0.3, (0.8, 0.8, 0.9, 0.9))
    # a garrafa vem com classes diferentes: na união, a classe não importa
    propor(saida, "t1_x.jpg", {"a": [GARRAFA, LATA], "b": [perto(LATA, 0.01),
                                                         ("Lata", 0.6, GARRAFA[2])],
                               "c": [perto(GARRAFA, 0.02), tampa]})
    assert votar.votar(saida, TRIO)["uniao"] == ["t1_x.jpg"]
    voto = formato.ler_voto(saida, "t1_x.jpg")
    assert [c["id"] for c in voto["caixas"]] == [None, None, None]
    garrafa, lata, so_c = voto["caixas"]
    assert garrafa["conf"] == pytest.approx(0.9)            # a maior das fundidas
    assert garrafa["caixa"] == pytest.approx([0.1, 0.1, 0.3, 0.3])   # a mediana
    assert {m["anotador"] for m in garrafa["membros"]} == set(TRIO)
    assert {m["anotador"] for m in lata["membros"]} == {"a", "b"}
    assert so_c["membros"] == [{"anotador": "c", "indice": 1}]


def test_unir_nao_funde_duas_caixas_do_mesmo_anotador():
    a1 = ("Garrafa", 0.9, (0.1, 0.1, 0.3, 0.3))
    a2 = ("Garrafa", 0.8, (0.11, 0.1, 0.31, 0.3))
    uniao = votar.unir([[a1, a2], [a1]])
    assert [m for *_, m in uniao] == [[(0, 0), (1, 0)], [(0, 1)]]


def test_votar_de_novo_so_com_proposta_nova_ou_revotar(tmp_path):
    saida = criar(tmp_path)
    concordam(saida, "l1_x.jpg")
    assert votar.votar(saida, TRIO)["aprovadas"] == ["l1_x.jpg"]
    r = votar.votar(saida, TRIO)
    assert (r["ja_votadas"], r["aprovadas"]) == (1, [])
    # c anota de novo e passa a discordar: o voto novo reprova e o rótulo some
    formato.nova_proposta(saida, "c", "l1_x.jpg", [GARRAFA], LIMIARES)
    assert votar.votar(saida, TRIO)["falhou"] == {"l1_x.jpg": "quantidade"}
    assert not (saida / "labels/l1_x.txt").exists()
    assert linhas(saida, "treino.txt") == []
    assert votar.votar(saida, TRIO, revotar=True)["falhou"] == {"l1_x.jpg": "quantidade"}
    with formato.abrir(saida) as con:
        assert con.execute("SELECT COUNT(*) FROM votos").fetchone()[0] == 3
        assert con.execute("SELECT COUNT(*) FROM votacoes").fetchone()[0] == 3


def test_classe_sugerida_e_limiares_de_leitura(tmp_path):
    saida = criar(tmp_path)
    fraca = ("Lata", 0.25, LATA[2])          # acima de confianca, abaixo de confianca_classe
    ruido = ("Tampa", 0.1, (0.8, 0.8, 0.9, 0.9))
    propor(saida, "l1_x.jpg", {"a": [fraca], "b": [fraca, ruido], "c": [fraca]})
    # a classe escondida do revisor vale no voto; a de 0,1 fica abaixo do limiar gravado
    assert votar.votar(saida, TRIO)["aprovadas"] == ["l1_x.jpg"]
    assert linhas(saida, "labels/l1_x.txt") == [formato.linha_yolo(1, LATA[2])]
    # com b lido em 0,05, o ruído entra e reprova
    r = votar.votar(saida, TRIO, limiares=[None, 0.05, None], revotar=True)
    assert r["falhou"] == {"l1_x.jpg": "quantidade"}
    assert [p["limiar"] for p in formato.ler_voto(saida, "l1_x.jpg")["propostas"]] == \
        [0.2, 0.05, 0.2]
    with pytest.raises(ValueError, match="um limiar por anotador"):
        votar.votar(saida, TRIO, limiares=[0.1])
    with pytest.raises(ValueError, match="dois anotadores"):
        votar.votar(saida, ["a", "a"])


def test_classe_fora_da_tabela_reprova(tmp_path):
    saida = criar(tmp_path)
    pneu = ("Pneu", 0.9, GARRAFA[2])
    propor(saida, "l1_x.jpg", {a: [pneu] for a in TRIO})
    assert votar.votar(saida, TRIO)["falhou"] == {"l1_x.jpg": "classe_fora"}


def test_revisao_humana_vale_mais_que_o_voto(tmp_path):
    saida = criar(tmp_path, {"l1": "treino", "t1": "teste"})
    concordam(saida, "l1_x.jpg")
    concordam(saida, "t1_x.jpg")
    votar.votar(saida, TRIO)
    # o revisor corrige a aprovada: o rótulo passa a ser o dele
    caixa = formato.ler_voto(saida, "l1_x.jpg")["caixas"][0]["caixa"]
    formato.revisar(saida, "l1_x.jpg", pedido(saida, "l1_x.jpg", caixas=[
        {"id": 2, "caixa": caixa, "origem": "voto", "indice": 0}]), "t")
    assert linhas(saida, "labels/l1_x.txt") == [formato.linha_yolo(2, caixa)]
    assert votar.votar(saida, TRIO)["aprovadas"] == []     # não é mais pendente
    assert linhas(saida, "treino.txt") == ["./images/l1_x.jpg"]
    # revisada de teste vai ao teste.txt, o val do data.yaml
    formato.revisar(saida, "t1_x.jpg", pedido(saida, "t1_x.jpg"), "t")
    assert linhas(saida, "teste.txt") == ["./images/t1_x.jpg"]
    assert linhas(saida, "revisadas.txt") == ["./images/l1_x.jpg", "./images/t1_x.jpg"]


def test_revisao_parte_do_voto_e_registra_a_origem(tmp_path):
    saida = criar(tmp_path)
    fora = ("Tampa", 0.3, (0.8, 0.8, 0.9, 0.9))       # só b, abaixo de confianca_classe
    fraca = ("Lata", 0.1, (0.6, 0.1, 0.7, 0.2))        # candidata de c
    ids = propor(saida, "l1_x.jpg", {"a": [GARRAFA, LATA], "b": [GARRAFA, fora],
                                     "c": [GARRAFA, fraca]})
    assert votar.votar(saida, TRIO)["falhou"] == {"l1_x.jpg": "quantidade"}
    base = formato.voto_para_revisao(saida, "l1_x.jpg", formato.nomes_classes(saida))
    assert (base["resultado"], base["motivo"], base["conjunto"]) == ("falhou", "quantidade",
                                                                  "treino")
    # uma caixa por objeto: a garrafa é consenso; a lata (só a) e a tampa (só b)
    # são conflitos, com a classe proposta como sugestão, mesmo abaixo de 0,35
    assert [(c["indice"], c["nome"], c["anotadores"]) for c in base["caixas"]] == \
        [(0, "Garrafa", TRIO), (1, None, ["a"]), (2, None, ["b"])]
    assert [c["sugestoes"] for c in base["caixas"]] == [
        [], [{"id": 1, "nome": "Lata", "anotadores": [{"anotador": "a", "conf": 0.8}]}],
        [{"id": 2, "nome": "Tampa", "anotadores": [{"anotador": "b", "conf": 0.3}]}]]
    assert "propostas" not in base
    assert [(c["anotador"], c["indice"]) for c in base["candidatas"]] == [("c", 1)]

    caixas = [{"id": 1, "caixa": list(GARRAFA[2]), "origem": "voto", "indice": 0},
              {"id": 1, "caixa": list(LATA[2]), "origem": "voto", "indice": 1},
              {"id": 2, "caixa": list(fraca[2]), "origem": "candidata", "anotador": "c",
               "indice": 1}]
    registro = formato.revisar(saida, "l1_x.jpg", pedido(saida, "l1_x.jpg", caixas=caixas,
                                                         tempo=12), "t")
    assert [(c["origem"], c["anotador"], c["indice"], c["desfecho"])
            for c in registro["caixas"]] == [("voto", None, 0, "classe_corrigida"),
                                             ("voto", None, 1, "classe_atribuida"),
                                             ("candidata", "c", 1, "adicionada")]
    assert registro["removidas"] == [2] and registro["voto_id"] == base["id"]
    with formato.abrir(saida) as con:
        assert {r[0] for r in con.execute("SELECT proposta_id FROM caixas_revisao "
                                          "WHERE proposta_id IS NOT NULL")} == {ids["c"]}
    assert len(linhas(saida, "labels/l1_x.txt")) == 3


def test_sugestoes_por_classe_dos_mais_votados_para_os_menos(tmp_path):
    saida = criar(tmp_path)
    caixa = GARRAFA[2]
    propor(saida, "l1_x.jpg", {"a": [("Lata", 0.6, caixa)], "b": [("Lata", 0.5, caixa)],
                               "c": [("Garrafa", 0.9, caixa), ("Pneu", 0.9, LATA[2])]})
    votar.votar(saida, TRIO)
    caixas = formato.voto_para_revisao(saida, "l1_x.jpg", formato.nomes_classes(saida))["caixas"]
    assert [(s["nome"], [q["anotador"] for q in s["anotadores"]])
            for s in caixas[0]["sugestoes"]] == [("Lata", ["a", "b"]), ("Garrafa", ["c"])]
    # classe fora do data.yaml não vira sugestão: o conflito vem sem nenhuma
    assert caixas[1]["sugestoes"] == []


def test_caixas_da_revisao_consenso_so_com_todos_na_mesma_classe():
    g, l = GARRAFA, LATA
    caixas = votar.caixas_da_revisao([[g, l], [perto(g, 0.01), l], [perto(g, 0.02)]])
    assert [(c[0], round(c[1], 2), c[3]) for c in caixas] == [
        ("Garrafa", 0.9, [(0, 0), (1, 0), (2, 0)]),     # os três, mesma classe
        (None, 0.8, [(0, 1), (1, 1)])]                  # dois de três: conflito


def test_teste_sem_pre_anotacao(tmp_path):
    saida = criar(tmp_path, {"t1": "teste"})
    concordam(saida, "t1_x.jpg")
    votar.votar(saida, TRIO)
    # a união sem classe fica gravada no voto, para comparar com a revisão...
    assert len(formato.ler_voto(saida, "t1_x.jpg")["caixas"]) == 2
    base = formato.voto_para_revisao(saida, "t1_x.jpg", formato.nomes_classes(saida))
    # ...mas a revisão do teste parte do zero (seção 4): nenhuma caixa, e todas
    # as caixas das propostas, também as visíveis, viram candidatas do clique
    assert base["caixas"] == []
    assert {c["origem"] for c in base["candidatas"]} == {"proposta"}
    assert len(base["candidatas"]) == 2   # as quase iguais dos três viram uma
    uma = base["candidatas"][0]
    caixa = {"id": 1, "caixa": uma["caixa"], "origem": "proposta", "anotador": uma["anotador"],
             "indice": uma["indice"]}
    registro = formato.revisar(saida, "t1_x.jpg", pedido(saida, "t1_x.jpg", caixas=[caixa]), "t")
    assert [c["desfecho"] for c in registro["caixas"]] == ["adicionada"]


def test_teste_recusa_caixa_do_voto(tmp_path):
    saida = criar(tmp_path, {"t1": "teste"})
    concordam(saida, "t1_x.jpg")
    votar.votar(saida, TRIO)
    caixa = formato.ler_voto(saida, "t1_x.jpg")["caixas"][0]["caixa"]
    with pytest.raises(formato.RevisaoInvalida, match="sem pré-anotação"):
        formato.revisar(saida, "t1_x.jpg", pedido(saida, "t1_x.jpg", caixas=[
            {"id": 1, "caixa": caixa, "origem": "voto", "indice": 0}]), "t")
    assert formato.ler_estado(saida)["t1_x.jpg"]["status"] == "pendente"


@pytest.mark.parametrize("caixa, trecho", [
    ({"id": 0, "caixa": [0.1, 0.1, 0.3, 0.3], "origem": "voto", "indice": 5}, "não tem a caixa 5"),
    ({"id": 0, "caixa": [0.1, 0.1, 0.4, 0.3], "origem": "voto", "indice": 0}, "coordenadas"),
    ({"id": 0, "caixa": [0.1, 0.1, 0.3, 0.3], "origem": "desenho", "indice": 0}, "origem"),
    ({"id": 0, "caixa": [0.1, 0.1, 0.3, 0.3], "origem": "proposta", "anotador": "z",
      "indice": 0}, "não usou proposta"),
    ({"id": 0, "caixa": [0.1, 0.1, 0.3, 0.3], "origem": "candidata", "anotador": "a",
      "indice": 0}, "não é candidata"),
    ({"id": 9, "caixa": [0.1, 0.1, 0.3, 0.3], "origem": "voto", "indice": 0}, "fora do data.yaml"),
])
def test_revisao_recusa_caixa_sem_origem_valida(tmp_path, caixa, trecho):
    saida = criar(tmp_path)
    concordam(saida, "l1_x.jpg")
    votar.votar(saida, TRIO)
    with pytest.raises(formato.RevisaoInvalida, match=trecho):
        formato.revisar(saida, "l1_x.jpg", pedido(saida, "l1_x.jpg", caixas=[caixa]), "t")
    duas = [{"id": 0, "caixa": [0.1, 0.1, 0.3, 0.3], "origem": "proposta", "anotador": "a",
             "indice": 0}] * 2
    with pytest.raises(formato.RevisaoInvalida, match="duas vezes"):
        formato.revisar(saida, "l1_x.jpg", pedido(saida, "l1_x.jpg", caixas=duas), "t")
    assert formato.ler_revisao(saida, "l1_x.jpg") is None


def test_exportar_refaz_rotulos_das_aprovadas(tmp_path):
    saida = criar(tmp_path)
    concordam(saida, "l1_x.jpg")
    votar.votar(saida, TRIO)
    original = linhas(saida, "labels/l1_x.txt")
    (saida / "labels/l1_x.txt").unlink()
    (saida / "labels/sobra.txt").write_text("0 0.5 0.5 0.1 0.1\n")
    (saida / "treino.txt").unlink()
    formato.exportar(saida)
    assert linhas(saida, "labels/l1_x.txt") == original
    assert not (saida / "labels/sobra.txt").exists()
    assert linhas(saida, "treino.txt") == ["./images/l1_x.jpg"]


def test_banco_de_outra_versao_e_recusado(tmp_path):
    caminho = formato.caminho_banco(tmp_path)
    con = sqlite3.connect(caminho, isolation_level=None)
    con.executescript(f"BEGIN; {formato.ESQUEMA} PRAGMA user_version = 2; COMMIT;")
    con.close()
    with pytest.raises(ValueError, match="versão 2.*importe de novo"):
        formato.preparar(tmp_path, NOMES)


def test_main_resume_e_recusa_anotador_sem_proposta(tmp_path, capsys):
    saida = criar(tmp_path)
    concordam(saida, "l1_x.jpg")
    votar.main([str(saida), "--anotadores", *TRIO])
    saida_texto = capsys.readouterr().out
    assert "1 imagem(ns) de treino votada(s), 0 de teste" in saida_texto and "aprovadas: 1 (100%)" in saida_texto
    with pytest.raises(ValueError, match="nenhuma proposta de grounding-dino"):
        votar.main([str(saida)])
    with pytest.raises(SystemExit):
        votar.main([str(saida), "--anotadores", "a", "b", "--limiares", "0.1"])
