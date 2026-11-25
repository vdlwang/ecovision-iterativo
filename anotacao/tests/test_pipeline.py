"""Testes da pipeline (pipeline.py), com anotadores sintéticos no lugar dos modelos."""

import json
import sys
from pathlib import Path

import pytest
import yaml
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import anotar  # noqa: E402
import pipeline  # noqa: E402
import saida as formato  # noqa: E402

NOMES = ["Lata", "Garrafa"]
CLASSES = [{"nome": "Lata", "prompt": "can", "material": "metal"},
           {"nome": "Garrafa", "prompt": "bottle", "material": "plastic"}]
LATA = (0, 0.9, (0.1, 0.1, 0.4, 0.4))
GARRAFA = (1, 0.8, (0.5, 0.5, 0.9, 0.9))
# Por nome original da imagem: "a" todos concordam; "b" o segundo acha uma garrafa a mais
DETECCOES = {
    "a": {"falso-1": [LATA], "falso-2": [LATA]},
    "b": {"falso-1": [LATA], "falso-2": [LATA, GARRAFA]},
}


def fabricar(tipo):
    """Um anotador sintético do tipo dado, que conta as imagens que anota."""
    class Falso:
        nome = tipo
        chamadas = []
        falhar_em = None   # nome original da imagem em que a rodada "cai"

        @staticmethod
        def opcoes(parser):
            parser.add_argument_group(tipo).add_argument(f"--{tipo}-versao", default="v1")

        @classmethod
        def criar(cls, classes, args):
            anotador = cls()
            anotador.versao = getattr(args, f"{tipo}_versao".replace("-", "_"))
            anotador.parametros = {"piso": args.piso}
            return anotador

        def anotar(self, imagem):
            original = imagem.info["stem"].split("_", 1)[1]
            if original == self.falhar_em:
                raise KeyboardInterrupt
            self.chamadas.append(original)
            return DETECCOES[original][tipo]
    return Falso


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    falsos = {t: fabricar(t) for t in ("falso-1", "falso-2")}
    monkeypatch.setattr(anotar, "MAX_CAIXAS_PADRAO", 0)  # várias caixas por imagem
    for tipo, classe in falsos.items():
        monkeypatch.setitem(anotar.ANOTADORES, tipo, classe)
    original = anotar.abrir_imagem

    def abrir(caminho):  # o anotador sintético sabe qual imagem recebeu
        imagem, girada = original(caminho)
        imagem.info["stem"] = Path(caminho).stem
        return imagem, girada
    monkeypatch.setattr(anotar, "abrir_imagem", abrir)

    fotos = tmp_path / "fotos"
    fotos.mkdir()
    for nome in DETECCOES:
        Image.new("RGB", (200, 100)).save(fotos / f"{nome}.jpg")
    classes = tmp_path / "classes.yaml"
    classes.write_text(yaml.safe_dump({"nomes": NOMES, "classes": CLASSES}), encoding="utf-8")
    config = escrever_config(tmp_path, {"anotadores": [
        {"nome": "falso-1", "tipo": "falso-1", "opcoes": {"confianca": 0.3}},
        {"nome": "falso-2", "tipo": "falso-2", "opcoes": {"falso-2-versao": "v7"}}]})
    saida = tmp_path / "saida"
    base = ["-o", str(saida), "--classes", str(classes), "--config", str(config)]
    return {"fotos": fotos, "saida": saida, "base": base, "falsos": falsos,
            "tmp": tmp_path}


def escrever_config(pasta, dados, nome="anotadores.yaml"):
    caminho = pasta / nome
    caminho.write_text(yaml.safe_dump(dados, allow_unicode=True), encoding="utf-8")
    return caminho


def votacoes(saida):
    with formato.abrir(saida) as con:
        return [json.loads(r["parametros"]) for r in con.execute(
            "SELECT parametros FROM votacoes ORDER BY id")]


def test_importa_anota_e_vota(ambiente):
    e = ambiente
    pipeline.main([str(e["fotos"]), "--lote", "l1", "--conjunto", "treino"] + e["base"])
    saida = e["saida"]
    estado = formato.ler_estado(saida)
    assert {n: l["voto"] for n, l in estado.items()} == {"l1_a.jpg": "aprovada",
                                                        "l1_b.jpg": "falhou"}
    assert estado["l1_b.jpg"]["motivo"] == "quantidade"
    assert (saida / "labels" / "l1_a.txt").exists()
    assert (saida / "treino.txt").read_text() == "./images/l1_a.jpg\n"
    # opções do yaml chegam ao anotador e à execução
    p1 = formato.ler_proposta(saida, "falso-1", "l1_a.jpg")
    p2 = formato.ler_proposta(saida, "falso-2", "l1_a.jpg")
    assert p1["parametros"]["confianca"] == 0.3 and p2["versao"] == "v7"
    # a votação grava a configuração usada
    [parametros] = votacoes(saida)
    assert [a["nome"] for a in parametros["configuracao"]["anotadores"]] == ["falso-1", "falso-2"]
    assert parametros["iou"] == 0.5 and parametros["auditoria"] == 0.05


def test_lote_de_teste_vira_uniao(ambiente):
    e = ambiente
    pipeline.main([str(e["fotos"]), "--lote", "t1", "--conjunto", "teste"] + e["base"])
    estado = formato.ler_estado(e["saida"])
    assert {l["voto"] for l in estado.values()} == {"uniao"}
    assert (e["saida"] / "treino.txt").read_text() == ""


def test_retoma_de_onde_parou(ambiente):
    e = ambiente
    f1, f2 = e["falsos"]["falso-1"], e["falsos"]["falso-2"]
    f2.falhar_em = "b"   # cai no segundo anotador, na segunda imagem
    with pytest.raises(KeyboardInterrupt):
        pipeline.main([str(e["fotos"]), "--lote", "l1", "--conjunto", "treino"] + e["base"])
    assert sorted(f1.chamadas) == ["a", "b"] and f2.chamadas == ["a"]
    assert formato.ler_proposta(e["saida"], "falso-2", "l1_a.jpg") is not None
    assert not votacoes(e["saida"])

    # O mesmo comando de novo: importação pulada, só a unidade (b, falso-2) roda
    f2.falhar_em = None
    f1.chamadas.clear()
    f2.chamadas.clear()
    pipeline.main([str(e["fotos"]), "--lote", "l1", "--conjunto", "treino"] + e["base"])
    assert f1.chamadas == [] and f2.chamadas == ["b"]
    assert {l["voto"] for l in formato.ler_estado(e["saida"]).values()} == {"aprovada", "falhou"}

    # Sem entradas, nada a anotar nem a votar
    f2.chamadas.clear()
    pipeline.main(e["base"])
    assert f2.chamadas == [] and len(votacoes(e["saida"])) == 1


def test_lote_novo_so_anota_o_novo(ambiente):
    e = ambiente
    pipeline.main([str(e["fotos"] / "a.jpg"), "--lote", "l1", "--conjunto", "treino"]
                  + e["base"])
    f1 = e["falsos"]["falso-1"]
    f1.chamadas.clear()
    pipeline.main([str(e["fotos"] / "b.jpg"), "--lote", "l2", "--conjunto", "treino"]
                  + e["base"])
    assert f1.chamadas == ["b"]
    assert set(formato.ler_estado(e["saida"])) == {"l1_a.jpg", "l2_b.jpg"}


@pytest.mark.parametrize("dados, erro", [
    ({"anotadores": [{"tipo": "falso-1"}]}, "ao menos dois"),
    ({"anotadores": [{"tipo": "falso-1"}, {"tipo": "nenhum"}]}, "tipo 'nenhum'"),
    ({"anotadores": [{"tipo": "falso-1"}, {"tipo": "falso-1"}]}, "'falso-1' repetido"),
    ({"anotadores": [{"tipo": "falso-1"}, {"tipo": "falso-2", "nome": "Maiúsculo"}]}, "nome"),
    ({"anotadores": [{"tipo": "falso-1", "opcoes": {"falso-2-versao": "v2"}},
                     {"tipo": "falso-2"}]}, "não aceita: falso-2-versao"),
    ({"anotadores": [{"tipo": "falso-1", "opcoes": {"previa": 1}}, {"tipo": "falso-2"}]},
     "não aceita: previa"),
    ({"anotadores": [{"tipo": "falso-1", "opcoes": {"piso": True}}, {"tipo": "falso-2"}]},
     "número ou texto"),
    ({"anotadores": [{"tipo": "falso-1", "extra": 1}, {"tipo": "falso-2"}]}, "desconhecidas"),
    ({"anotadores": [{"tipo": "falso-1"}, {"tipo": "falso-2"}], "voto": {"iou": 2}}, "iou"),
    ({"anotadores": [{"tipo": "falso-1"}, {"tipo": "falso-2"}], "voto": {"auditoria": -1}},
     "auditoria"),
    ({"anotadores": [{"tipo": "falso-1"}, {"tipo": "falso-2"}], "outra": 1}, "desconhecidas"),
])
def test_config_invalida(ambiente, dados, erro):
    caminho = escrever_config(ambiente["tmp"], dados, "ruim.yaml")
    with pytest.raises(ValueError, match=erro):
        pipeline.carregar_config(caminho)


def test_erro_num_anotador_antes_de_mexer_na_saida(ambiente):
    e = ambiente
    # o segundo tem limiares invertidos: o anotar.py recusa, e nada roda
    config = escrever_config(e["tmp"], {"anotadores": [
        {"tipo": "falso-1"}, {"tipo": "falso-2", "opcoes": {"piso": 0.5, "confianca": 0.2}}]},
        "invertido.yaml")
    base = e["base"][:-1] + [str(config)]
    with pytest.raises(ValueError, match="anotador 'falso-2'"):
        pipeline.main([str(e["fotos"]), "--lote", "l1"] + base)
    assert not e["saida"].exists()
    assert e["falsos"]["falso-1"].chamadas == []


def test_opcoes_de_importacao_so_com_entradas(ambiente):
    e = ambiente
    with pytest.raises(SystemExit):
        pipeline.main(e["base"] + ["--lote", "l1"])
    with pytest.raises(SystemExit):
        pipeline.main(e["base"] + ["--janela", "5"])
    with pytest.raises(SystemExit):
        pipeline.main([str(e["fotos"])] + e["base"] + ["--lote", "l1", "--janela", "-1"])
    with pytest.raises(SystemExit):
        pipeline.main([str(e["fotos"])] + e["base"])        # entradas sem --lote
    with pytest.raises(SystemExit):
        pipeline.main(e["base"])                            # saída sem importação


def test_max_caixas_vai_a_todos_os_anotadores():
    anotador = {"nome": "a", "tipo": "grounding-dino", "opcoes": {"max-caixas": 3}}
    argv = pipeline.argv_anotador(anotador, "saida", "classes.yaml", max_caixas=0)
    _, args = anotar.ler_argumentos(argv)
    assert args.max_caixas == 0
    _, args = anotar.ler_argumentos(pipeline.argv_anotador(anotador, "saida", "classes.yaml"))
    assert args.max_caixas == 3


def test_anotadores_yaml_do_repositorio_e_valido():
    config = pipeline.carregar_config(pipeline.CONFIG_PADRAO)
    assert [a["nome"] for a in config["anotadores"]] == ["grounding-dino", "owlv2", "yolo"]
    argvs = [pipeline.argv_anotador(a, "saida", pipeline.DIR_SCRIPT / "classes.yaml")
             for a in config["anotadores"]]
    pipeline.conferir_argumentos(config, argvs)   # sem carregar modelo
