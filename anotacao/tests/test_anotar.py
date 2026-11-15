"""Testes das funções do anotar.py que não dependem do modelo."""

import json
import sys
from pathlib import Path

import pytest
import yaml
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import anotar  # noqa: E402
import importar  # noqa: E402
import saida as formato  # noqa: E402
import votar  # noqa: E402
from auxiliar import pedido, votar_imagens  # noqa: E402

CLASSES = [
    {"nome": "Garrafa", "prompt": "Plastic bottle", "material": "plastic"},
    {"nome": "Tampa", "prompt": "plastic bottle cap", "material": "plastic"},
    {"nome": "Lata", "prompt": "can", "material": "metal"},
]


def test_montar_prompt_formato_e_intervalos():
    texto, intervalos = anotar.montar_prompt(CLASSES)
    assert texto == "plastic bottle . plastic bottle cap . can ."
    assert [(texto[a:b], c) for a, b, c in intervalos] == [
        ("plastic bottle", 0), ("plastic bottle cap", 1), ("can", 2)]


def test_varios_prompts_por_classe():
    classes = [{"nome": "Garrafa", "prompt": ["Plastic bottle", "pet bottle"],
                "material": "plastic"},
               {"nome": "Lata", "prompt": "can", "material": "metal"}]
    assert anotar.prompts(classes[0]) == ["plastic bottle", "pet bottle"]
    texto, intervalos = anotar.montar_prompt(classes)
    assert texto == "plastic bottle . pet bottle . can ."
    assert [(texto[a:b], c) for a, b, c in intervalos] == [
        ("plastic bottle", 0), ("pet bottle", 0), ("can", 1)]
    offsets = [(0, 0), (0, 7), (8, 14), (15, 16), (17, 20), (21, 27), (28, 29),
               (30, 33), (34, 35), (0, 0)]
    assert anotar.classe_de_cada_token(offsets, intervalos) == [
        None, 0, 0, None, 0, 0, None, 1, None, None]


def test_classe_de_cada_token_ignora_especiais_e_pontos():
    texto, intervalos = anotar.montar_prompt(CLASSES)
    # offsets como os de um tokenizer BERT: [CLS], palavras, pontos, [SEP]
    offsets = [(0, 0)]
    pos = 0
    for palavra in texto.split(" "):
        offsets.append((pos, pos + len(palavra)))
        pos += len(palavra) + 1
    offsets.append((0, 0))
    assert anotar.classe_de_cada_token(offsets, intervalos) == [
        None, 0, 0, None, 1, 1, 1, None, 2, None, None]


def test_escolher_classe_com_reserva():
    # sem reserva: a de maior pontuação, mesmo abaixo do limiar
    assert anotar.escolher_classe([0.1, 0.3, 0.2], frozenset(), 0.35) == (1, 0.3)
    # a reserva (2) não tira de uma comum que chega ao limiar...
    assert anotar.escolher_classe([0.4, 0.1, 0.9], frozenset({2}), 0.35) == (0, 0.4)
    # ...só vence quando nenhuma comum chega e ela chega
    assert anotar.escolher_classe([0.2, 0.1, 0.5], frozenset({2}), 0.35) == (2, 0.5)
    assert anotar.escolher_classe([0.2, 0.1, 0.3], frozenset({2}), 0.35) == (0, 0.2)


def test_carregar_classes_valida_reserva(tmp_path):
    reserva = {"nome": "Lixo", "prompt": "trash", "material": "other", "reserva": True}
    assert anotar.carregar_classes(escrever_classes(tmp_path, CLASSES + [reserva]))[-1] == reserva
    with pytest.raises(ValueError, match="ao menos uma"):
        anotar.carregar_classes(escrever_classes(tmp_path, [reserva]))
    with pytest.raises(ValueError, match="reserva"):
        anotar.carregar_classes(escrever_classes(tmp_path, [dict(reserva, reserva="sim")]))


def test_iou():
    assert anotar.iou((0, 0, 1, 1), (0, 0, 1, 1)) == 1
    assert anotar.iou((0, 0, 1, 1), (2, 2, 3, 3)) == 0
    assert anotar.iou((0, 0, 2, 1), (1, 0, 3, 1)) == pytest.approx(1 / 3)


def test_nms_suprime_sobreposta_de_qualquer_classe():
    a = (0, 0.9, (0.1, 0.1, 0.5, 0.5))
    b = (1, 0.6, (0.12, 0.1, 0.5, 0.52))   # mesmo objeto, outro prompt
    c = (2, 0.7, (0.6, 0.6, 0.9, 0.9))
    assert anotar.nms([b, c, a], 0.5) == [a, c]


def test_contida():
    assert anotar.contida((0.2, 0.2, 0.4, 0.4), (0, 0, 1, 1)) == 1
    assert anotar.contida((0, 0, 1, 1), (0.2, 0.2, 0.4, 0.4)) == pytest.approx(0.04)
    assert anotar.contida((0.5, 0, 1.5, 1), (0, 0, 1, 1)) == pytest.approx(0.5)
    assert anotar.contida((0.3, 0.3, 0.3, 0.5), (0, 0, 1, 1)) == 0  # sem área


def test_sem_contidas_remove_a_interna_menos_confiante():
    lata = (0, 0.37, (0.3, 0.3, 0.5, 0.5))
    topo_fraco = (1, 0.33, (0.32, 0.32, 0.45, 0.45))   # dentro da lata, menos confiante: sai
    topo_forte = (1, 0.38, (0.31, 0.31, 0.46, 0.46))   # dentro da lata, mais confiante: fica
    envolvente = (2, 0.22, (0.25, 0.25, 0.6, 0.6))     # envolve mais confiantes: fica
    longe = (0, 0.2, (0.7, 0.7, 0.8, 0.8))
    meio_dentro = (0, 0.1, (0.55, 0.3, 0.65, 0.4))     # metade dentro da envolvente: fica
    deteccoes = [lata, topo_fraco, topo_forte, envolvente, longe, meio_dentro]
    assert anotar.sem_contidas(deteccoes, 0.9) == [lata, topo_forte, envolvente, longe,
                                                   meio_dentro]
    assert anotar.sem_contidas(deteccoes, 0.45) == [lata, topo_forte, envolvente, longe]
    assert anotar.sem_contidas(deteccoes, 1.01) == deteccoes  # desligado


class DetectorFalso(anotar.Detector):
    """Só implementa o que é do modelo: tudo o mais vem da base."""
    nome = "detector-falso"
    MODELO_PADRAO = "falso-v1"

    def carregar(self):
        self.carregado = True

    def pontuar(self, imagem):
        # 3 classes (Garrafa, Tampa, Lata); pontuações por caixa
        return [[0.10, 0.02, 0.90],   # Lata 0,90
                [0.30, 0.01, 0.05],   # Garrafa 0,30, dentro da Lata: contida, sai
                [0.04, 0.03, 0.01],   # abaixo do piso
                [0.20, 0.06, 0.02],   # Garrafa 0,20, grande demais
                [0.02, 0.08, 0.03]], [  # Tampa 0,08, isolada
            (0.1, 0.1, 0.5, 0.5), (0.2, 0.2, 0.3, 0.3), (0.6, 0.6, 0.7, 0.7),
            (0.0, 0.0, 1.0, 0.9), (0.8, 0.0, 0.9, 0.1)]


def test_detector_base_filtra_o_que_o_modelo_pontua():
    detector = DetectorFalso(CLASSES)
    assert detector.carregado and detector.versao == "falso-v1"
    assert detector.parametros == {"piso": anotar.PISO_PADRAO, "confianca": anotar.CONFIANCA_PADRAO,
                                   "confianca_classe": anotar.CONFIANCA_CLASSE_PADRAO,
                                   "iou": 0.5, "area_maxima": 0.5, "contencao": 0.9}
    assert detector.anotar(None) == [(2, 0.90, (0.1, 0.1, 0.5, 0.5)),
                                     (1, 0.08, (0.8, 0.0, 0.9, 0.1))]
    # piso mais alto (avaliar.py), e sem contenção a Garrafa contida volta
    assert [c for c, _, _ in detector.filtrar(*detector.pontuar(None), piso=0.5)] == [2]
    sem = DetectorFalso(CLASSES, modelo="outro", contencao=1.01)
    assert sem.versao == "outro"
    assert [c for c, _, _ in sem.anotar(None)] == [2, 0, 1]
    with pytest.raises(ValueError, match="piso"):
        DetectorFalso(CLASSES, piso=0.3, confianca=0.2)


def test_caixas_owlv2_desfaz_o_quadrado_do_processador():
    # imagem 400x200: o processador completa embaixo até 400x400, e as caixas
    # vêm normalizadas pelo quadrado
    paisagem = anotar.caixas_owlv2([(0.5, 0.25, 0.5, 0.25), (0.9, 0.45, 0.4, 0.3)], 400, 200)
    assert paisagem[0] == pytest.approx((0.25, 0.25, 0.75, 0.75))
    assert paisagem[1] == pytest.approx((0.7, 0.6, 1.0, 1.0))  # recortada à imagem
    retrato = anotar.caixas_owlv2([(0.25, 0.5, 0.5, 0.5)], 200, 400)
    assert retrato[0] == pytest.approx((0.0, 0.25, 1.0, 0.75))


def test_owlv2_registrado_e_frase_validada_antes_do_modelo():
    assert anotar.ANOTADORES["owlv2"] is anotar.Owlv2
    with pytest.raises(ValueError, match="sem"):
        anotar.Owlv2(CLASSES, frase="a photo")


def test_colunas_yolo_casa_pelo_nome():
    modelo = {0: "Lata", 1: "Outra", 2: "Garrafa", 3: "Tampa"}
    assert anotar.colunas_yolo(CLASSES, modelo) == [2, 3, 0]
    with pytest.raises(ValueError, match="Tampa"):
        anotar.colunas_yolo(CLASSES, {0: "Lata", 2: "Garrafa"})
    assert anotar.ANOTADORES["yolo"] is anotar.Yolo


def test_criar_passa_os_argumentos_proprios_do_detector():
    class ComFrase(DetectorFalso):
        @classmethod
        def argumentos(cls, args):
            return {"frase": args.frase}

        def __init__(self, classes, frase=None, **kwargs):
            self.frase = frase
            super().__init__(classes, **kwargs)

    args = anotar.argparse.Namespace(
        modelo=None, dispositivo=None, piso=0.05, confianca=0.2, confianca_classe=0.35,
        iou=0.5, area_maxima=0.5, contencao=0.9, frase="a {}")
    assert ComFrase.criar(CLASSES, args).frase == "a {}"


def test_linha_yolo():
    assert anotar.linha_yolo(3, (0.2, 0.4, 0.6, 0.5)) == "3 0.400000 0.450000 0.400000 0.100000"


def escrever_classes(tmp_path, classes):
    caminho = tmp_path / "classes.yaml"
    caminho.write_text(yaml.safe_dump({"classes": classes}), encoding="utf-8")
    return caminho


def test_carregar_classes_valida(tmp_path):
    assert anotar.carregar_classes(escrever_classes(tmp_path, CLASSES)) == CLASSES
    with pytest.raises(ValueError, match="material"):
        anotar.carregar_classes(escrever_classes(
            tmp_path, [{"nome": "x", "prompt": "x", "material": "vidro"}]))
    with pytest.raises(ValueError, match="repetida"):
        anotar.carregar_classes(escrever_classes(tmp_path, [CLASSES[0], CLASSES[0]]))
    with pytest.raises(ValueError, match="prompt"):
        anotar.carregar_classes(escrever_classes(tmp_path, [{"nome": "x", "material": "metal"}]))
    lista = {"nome": "Garrafa", "prompt": ["a", "b"], "material": "plastic"}
    assert anotar.carregar_classes(escrever_classes(tmp_path, [lista])) == [lista]
    for ruim in ([], ["a", ""], [1], ["a", "A "]):
        with pytest.raises(ValueError, match="prompt"):
            anotar.carregar_classes(escrever_classes(
                tmp_path, [{"nome": "x", "prompt": ruim, "material": "metal"}]))


def test_classes_yaml_do_repositorio_e_valido():
    assert anotar.carregar_classes(anotar.DIR_SCRIPT / "classes.yaml")
    nomes = anotar.carregar_nomes(anotar.DIR_SCRIPT / "classes.yaml")
    # TACO + Background, na ordem do legado/database e do best.pt
    legado = anotar.DIR_SCRIPT.parent / "legado/database/tcc-0CF/YOLO_dataset/data.yaml"
    assert nomes == yaml.safe_load(legado.read_text(encoding="utf-8"))["names"]
    assert len(nomes) == 61 and nomes[-1] == "Background"


def test_carregar_nomes(tmp_path):
    # Sem 'nomes', os de 'classes', na ordem delas
    assert anotar.carregar_nomes(escrever_classes(tmp_path, CLASSES)) == ["Garrafa", "Tampa", "Lata"]
    caminho = tmp_path / "c.yaml"
    caminho.write_text(yaml.safe_dump({"nomes": ["Lata", "Fundo", "Garrafa"],
                                       "classes": CLASSES[::2]}), encoding="utf-8")
    assert anotar.carregar_nomes(caminho) == ["Lata", "Fundo", "Garrafa"]
    assert anotar.carregar_classes(caminho) == CLASSES[::2]
    caminho.write_text(yaml.safe_dump({"nomes": ["Lata"], "classes": CLASSES}), encoding="utf-8")
    with pytest.raises(ValueError, match="fora de 'nomes': Garrafa, Tampa"):
        anotar.carregar_classes(caminho)
    caminho.write_text(yaml.safe_dump({"nomes": ["Lata", "Lata"]}), encoding="utf-8")
    with pytest.raises(ValueError, match="repetidos: Lata"):
        anotar.carregar_nomes(caminho)


# --- anotar.py de ponta a ponta, com um anotador sintético no lugar do modelo ---

# Os ids dos rótulos vêm de 'nomes', não da ordem de 'classes'
NOMES = ["Fundo", "Lata", "Garrafa", "Tampa"]
DETECCOES = {
    "a": [(2, 0.91, (0.1, 0.2, 0.4, 0.6)), (0, 0.42, (0.5, 0.5, 0.9, 0.8))],
    "b": [],
}


class AnotadorFalso:
    nome = "falso"

    @staticmethod
    def opcoes(parser):
        parser.add_argument_group("falso").add_argument("--falso-versao", default="v1")

    @classmethod
    def criar(cls, classes, args):
        anotador = cls()
        anotador.versao = args.falso_versao
        anotador.parametros = {}
        return anotador

    def anotar(self, imagem):
        # nome importado: <lote>_<nome original>
        return DETECCOES[imagem.info["stem"].split("_", 1)[1]]


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    monkeypatch.setitem(anotar.ANOTADORES, "falso", AnotadorFalso)
    original = anotar.abrir_imagem

    def abrir(caminho):  # deixa o anotador falso saber qual imagem recebeu
        imagem, girada = original(caminho)
        imagem.info["stem"] = Path(caminho).stem
        return imagem, girada
    monkeypatch.setattr(anotar, "abrir_imagem", abrir)

    fotos = tmp_path / "fotos"
    fotos.mkdir()
    for nome in ("a.jpg", "b.png"):
        Image.new("RGB", (200, 100)).save(fotos / nome)
    classes = tmp_path / "classes.yaml"
    classes.write_text(yaml.safe_dump({"nomes": NOMES, "classes": CLASSES}), encoding="utf-8")
    saida = tmp_path / "saida"
    importar.main([str(fotos), "-o", str(saida), "--lote", "l1", "--conjunto", "treino",
                   "--classes", str(classes)])
    base = ["-o", str(saida), "--anotador", "falso", "--classes", str(classes)]
    return fotos, saida, base


def proposta_de(saida, nome):
    return formato.ler_proposta(saida, "falso", nome)


def estado_de(saida):
    return [(n, l["status"], l["lote"], l["conjunto"]) for n, l in formato.ler_estado(saida).items()]


def test_main_anota_as_importadas_sem_copiar(ambiente, capsys):
    _, saida, base = ambiente
    imagens_antes = sorted(p.name for p in (saida / "images").iterdir())
    anotar.main(base + ["--previa"])

    proposta = proposta_de(saida, "l1_a.jpg")
    assert proposta["anotador"] == proposta["tipo"] == "falso" and proposta["versao"] == "v1"
    assert proposta["imagem"] == "l1_a.jpg"
    assert proposta["classes"] == formato.hash_classes(CLASSES)
    assert proposta["caixas"][0] == ("Lata", 0.91, (0.1, 0.2, 0.4, 0.6))
    assert proposta_de(saida, "l1_b.png")["caixas"] == []
    assert estado_de(saida) == [("l1_a.jpg", "pendente", "l1", "treino"),
                                ("l1_b.png", "pendente", "l1", "treino")]
    assert (saida / "anotacoes.sqlite.bak").exists()
    assert sorted(p.name for p in (saida / "images").iterdir()) == imagens_antes
    assert not list((saida / "labels").iterdir())
    assert (saida / "revisadas.txt").read_text() == ""
    assert yaml.safe_load((saida / "data.yaml").read_text())["names"] == dict(enumerate(NOMES))
    assert (saida / "previa" / "falso" / "l1_a.jpg").exists()
    assert (saida / "visualizar.html").exists()

    # De novo, sem nomes: nada a anotar (todas já têm proposta)
    anotar.main(base)
    assert "Nada a anotar" in capsys.readouterr().out
    with pytest.raises(SystemExit):  # já anotada por este anotador
        anotar.main(["l1_a.jpg"] + base)
    with pytest.raises(SystemExit):  # não importada
        anotar.main(["c.jpg"] + base)
    primeira = proposta_de(saida, "l1_a.jpg")["id"]
    anotar.main(["l1_a.jpg"] + base + ["--sobrescrever", "--falso-versao", "v2"])
    assert proposta_de(saida, "l1_a.jpg")["versao"] == "v2"
    assert proposta_de(saida, "l1_b.png")["versao"] == "v1"
    # a anterior continua no banco
    assert formato.ler_proposta(saida, "falso", "l1_a.jpg", primeira)["versao"] == "v1"


def test_main_so_anota_pendentes(ambiente, capsys):
    _, saida, base = ambiente
    anotar.main(base)
    votar_imagens(saida, ["l1_b.png"])
    formato.revisar(saida, "l1_b.png", pedido(saida, "l1_b.png", "descartar"), "t")
    anotar.main(base + ["--sobrescrever", "--falso-versao", "v2"])
    assert proposta_de(saida, "l1_a.jpg")["versao"] == "v2"
    assert proposta_de(saida, "l1_b.png")["versao"] == "v1"  # descartada: intocada
    anotar.main(["l1_b.png"] + base + ["--sobrescrever", "--falso-versao", "v3"])
    assert "Puladas (já descartada): l1_b.png" in capsys.readouterr().out
    assert proposta_de(saida, "l1_b.png")["versao"] == "v1"


def test_main_regiao_de_interesse_pelo_centro(tmp_path, ambiente):
    fotos, saida, base = ambiente
    classes = base[base.index("--classes") + 1]
    # Lote com região à esquerda: a Lata (centro x=0,25) fica, a Garrafa (0,7) sai
    importar.main([str(fotos / "a.jpg"), "-o", str(saida), "--lote", "l2", "--regiao",
                   "0", "0", "0.3", "1", "--classes", classes])
    anotar.main(["l2_a.jpg"] + base)
    assert [c[0] for c in proposta_de(saida, "l2_a.jpg")["caixas"]] == ["Lata"]


def test_main_votado_reproduz_os_rotulos_de_antes(ambiente):
    _, saida, base = ambiente
    anotar.main(base)
    anotar.main(base + ["--nome", "falso-b"])
    votar.votar(saida, ["falso", "falso-b"])
    # Dois anotadores iguais: a aprovada tem os mesmos .txt que o anotar.py
    # gravava antes, direto das detecções, com o id de cada classe em NOMES
    esperado = "".join(anotar.linha_yolo(NOMES.index(CLASSES[c]["nome"]), caixa) + "\n"
                       for c, _, caixa in DETECCOES["a"])
    assert (saida / "labels" / "l1_a.txt").read_text() == esperado
    assert not (saida / "labels" / "l1_b.txt").exists()   # sem objeto: falhou (vazia)
    assert (saida / "treino.txt").read_text() == "./images/l1_a.jpg\n"
    # --exportar refaz os rótulos do banco
    (saida / "labels" / "l1_a.txt").unlink()
    anotar.main(base + ["--exportar"])
    assert (saida / "labels" / "l1_a.txt").read_text() == esperado


def test_main_grava_tudo_e_os_limiares_de_leitura(ambiente):
    _, saida, base = ambiente
    anotar.main(["l1_a.jpg"] + base + ["--confianca", "0.5", "--confianca-classe", "0.95",
                                       "--previa"])
    proposta = proposta_de(saida, "l1_a.jpg")
    # A proposta guarda todas as caixas, com a classe; os limiares vão em parametros
    assert [(c[0], c[1]) for c in proposta["caixas"]] == [
        ("Lata", 0.91), ("Garrafa", 0.42)]
    assert proposta["parametros"] == {"confianca": 0.5, "confianca_classe": 0.95}
    visiveis, candidatas = formato.separar(proposta)
    assert list(visiveis) == [0] and visiveis[0][3] is False  # 0,91 < 0,95: sem classe
    assert [k for k, _, _ in candidatas] == [1]


def test_main_recusa_limiares_invertidos(ambiente):
    _, _, base = ambiente
    with pytest.raises(SystemExit):
        anotar.main(base + ["--piso", "0.3", "--confianca", "0.2"])


def test_main_recusa_saida_sem_importacao(tmp_path, ambiente):
    _, _, base = ambiente
    base = list(base)
    base[base.index("-o") + 1] = str(tmp_path / "vazia")
    with pytest.raises(SystemExit):
        anotar.main(base)


def test_main_nome_separa_o_anotador_do_tipo(ambiente):
    _, saida, base = ambiente
    anotar.main(base + ["--nome", "falso-b"])
    proposta = formato.ler_proposta(saida, "falso-b", "l1_a.jpg")
    assert (proposta["anotador"], proposta["tipo"]) == ("falso-b", "falso")
    assert formato.anotadores(saida) == ["falso-b"]
    with pytest.raises(SystemExit):
        anotar.main(base + ["--nome", "Maiúsculo"])
