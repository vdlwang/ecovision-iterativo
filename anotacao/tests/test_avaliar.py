"""Testes das funções do avaliar.py que não dependem do modelo."""

import sys
from collections import Counter
from pathlib import Path

import json

import pytest
import yaml
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import avaliar  # noqa: E402
import importar  # noqa: E402
import saida as formato  # noqa: E402

NOMES_DATASET = ["Battery", "Clear plastic bottle", "Drink can"]
NOMES = ["Drink can", "Clear plastic bottle"]


def test_ler_verdade_caixa_poligono_e_classes_de_fora(tmp_path):
    rotulo = tmp_path / "foto.txt"
    rotulo.write_text("1 0.5 0.5 0.2 0.4\n"
                      "2 0.1 0.2 0.3 0.2 0.3 0.6 0.1 0.6\n"
                      "\n"
                      "0 0.5 0.5 0.1 0.1\n", encoding="utf-8")
    verdade, fora = avaliar.ler_verdade(rotulo, NOMES_DATASET, NOMES)
    assert [c for c, _ in verdade] == [1, 0]
    assert verdade[0][1] == pytest.approx((0.4, 0.3, 0.6, 0.7))
    assert verdade[1][1] == pytest.approx((0.1, 0.2, 0.3, 0.6))
    assert fora == Counter({"Battery": 1})


def test_ler_verdade_recusa_linha_invalida(tmp_path):
    rotulo = tmp_path / "foto.txt"
    rotulo.write_text("1 0.5 0.5 0.2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="inválida"):
        avaliar.ler_verdade(rotulo, NOMES_DATASET, NOMES)


def test_nomes_do_dataset_na_pasta_de_cima_e_como_dicionario(tmp_path):
    split = tmp_path / "validation"
    split.mkdir()
    (tmp_path / "data.yaml").write_text("names: {0: a, 1: b}\n", encoding="utf-8")
    assert avaliar.nomes_do_dataset(split) == ["a", "b"]
    with pytest.raises(ValueError, match="data.yaml"):
        avaliar.nomes_do_dataset(tmp_path / "outra" / "validation")


def test_casar_exige_classe_e_casa_cada_verdadeira_uma_vez():
    verdade = [(0, (0.1, 0.1, 0.3, 0.3)), (1, (0.5, 0.5, 0.9, 0.9))]
    deteccoes = [
        (0, 0.9, (0.1, 0.1, 0.3, 0.3)),     # acerto
        (0, 0.8, (0.1, 0.1, 0.31, 0.3)),    # mesma caixa de novo: falso positivo
        (0, 0.7, (0.5, 0.5, 0.9, 0.9)),     # lugar certo, classe errada
    ]
    assert avaliar.casar(deteccoes, verdade) == (1, 2, 1)
    assert avaliar.casar([], verdade) == (0, 0, 2)


def test_ler_verdade_aplica_e_confere_correcoes(tmp_path):
    rotulo = tmp_path / "foto.txt"
    rotulo.write_text("1 0.5 0.5 0.2 0.4\n\n0 0.5 0.5 0.1 0.1\n", encoding="utf-8")
    # linha 3: Battery vira Drink can e passa a contar
    verdade, fora = avaliar.ler_verdade(rotulo, NOMES_DATASET, NOMES,
                                        {3: ("Battery", "Drink can")})
    assert [c for c, _ in verdade] == [1, 0] and not fora
    with pytest.raises(ValueError, match="esperava"):
        avaliar.ler_verdade(rotulo, NOMES_DATASET, NOMES, {1: ("Drink can", "Battery")})
    with pytest.raises(ValueError, match="não existem"):
        avaliar.ler_verdade(rotulo, NOMES_DATASET, NOMES, {9: ("Battery", "Drink can")})


def test_carregar_correcoes_recusa_linha_repetida(tmp_path):
    caminho = tmp_path / "c.yaml"
    caminho.write_text("correcoes:\n  a/b.txt:\n    - {linha: 1, de: x, para: y}\n"
                       "    - {linha: 1, de: x, para: z}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duas vezes"):
        avaliar.carregar_correcoes(caminho)


def test_correcoes_do_repositorio_batem_com_os_rotulos():
    """Toda correção aponta para um .txt e uma linha que existem, com a classe 'de'."""
    correcoes = avaliar.carregar_correcoes(avaliar.CORRECOES_PADRAO)
    assert sum(len(c) for c in correcoes.values()) == 97
    for rotulo, por_linha in correcoes.items():
        assert rotulo.exists(), rotulo
        nomes_dataset = avaliar.nomes_do_dataset(rotulo.parent.parent)
        avaliar.ler_verdade(rotulo, nomes_dataset, nomes_dataset, por_linha)


def test_casar_sem_classe_um_par_por_caixa():
    verdade = [(0, (0.1, 0.1, 0.3, 0.3)), (1, (0.5, 0.5, 0.9, 0.9))]
    deteccoes = [(1, 0.9, (0.1, 0.1, 0.3, 0.3)),     # classe errada: casa mesmo assim
                 (0, 0.8, (0.1, 0.1, 0.31, 0.3)),    # a mesma verdadeira: não casa de novo
                 (1, 0.7, (0.0, 0.0, 0.05, 0.05))]   # longe
    assert avaliar.casar_sem_classe(deteccoes, verdade) == [(0, 0)]
    assert avaliar.casar_sem_classe(deteccoes[1:], verdade) == [(0, 0)]


def test_nome_original_tira_so_o_prefixo_do_lote():
    assert avaliar.nome_original("tcc-0CF_20250503_140329.jpg", "tcc-0CF") == "20250503_140329.jpg"
    assert avaliar.nome_original("20250503_140329.jpg", "") == "20250503_140329.jpg"
    assert avaliar.nome_original("outro_a.jpg", "l1") == "outro_a.jpg"


def dataset(pasta, rotulos):
    """Pasta no formato YOLO: images/, labels/ e data.yaml com Garrafa, Lata, Pilha."""
    (pasta / "images").mkdir(parents=True)
    (pasta / "labels").mkdir()
    (pasta / "data.yaml").write_text(yaml.safe_dump({"names": ["Garrafa", "Lata", "Pilha"]}))
    for nome, linhas in rotulos.items():
        Image.new("RGB", (100, 100)).save(pasta / "images" / nome)
        if linhas is not None:
            (pasta / "labels" / f"{Path(nome).stem}.txt").write_text("".join(
                f"{c} {(x1 + x2) / 2} {(y1 + y2) / 2} {x2 - x1} {y2 - y1}\n"
                for c, (x1, y1, x2, y2) in linhas))


def test_indexar_verdade_recusa_nome_em_duas_pastas(tmp_path):
    dataset(tmp_path / "v1", {"a.jpg": []})
    dataset(tmp_path / "v2", {"a.jpg": []})
    assert set(avaliar.indexar_verdade([tmp_path / "v1"])) == {"a.jpg"}
    with pytest.raises(ValueError, match="mais de uma pasta"):
        avaliar.indexar_verdade([tmp_path / "v1", tmp_path / "v2"])


A, B, C = (0.1, 0.1, 0.3, 0.3), (0.6, 0.6, 0.8, 0.8), (0.4, 0.4, 0.6, 0.6)
CLASSES = [{"nome": "Garrafa", "prompt": "bottle", "material": "plastic"},
           {"nome": "Lata", "prompt": "can", "material": "metal"}]


def test_avaliar_de_ponta_a_ponta_sem_modelo(tmp_path):
    verdade = tmp_path / "validacao-equipe"
    dataset(verdade, {"a.jpg": [(0, A), (1, B), (2, (0.0, 0.0, 0.05, 0.05))],  # Pilha: fora
                      "b.jpg": [(1, C)], "c.jpg": None})                       # c: sem rótulo
    saida = tmp_path / "saida"
    importar.importar(saida, sorted((verdade / "images").iterdir()), "val", ["Garrafa", "Lata"],
                      conjunto="teste")
    parametros = {"piso": 0.05, "confianca": 0.2, "confianca_classe": 0.35}
    propostas = {
        "a.jpg": [(0, 0.9, A),                      # certa
                  (0, 0.3, B),                      # cobre a Lata com a classe errada
                  (1, 0.1, (0.0, 0.6, 0.1, 0.7))],  # candidata que sobra
        "b.jpg": [(1, 0.12, C)],                    # só uma candidata cobre a Lata
        "c.jpg": []}
    for nome, deteccoes in propostas.items():
        formato.nova_proposta(saida, "falso", f"val_{nome}",
                              [(CLASSES[c]["nome"], conf, caixa) for c, conf, caixa in deteccoes],
                              parametros, versao="v1")

    destino = tmp_path / "r.json"
    classes = tmp_path / "classes.yaml"
    classes.write_text(yaml.safe_dump({"classes": CLASSES}), encoding="utf-8")
    avaliar.main([str(saida), "--anotador", "falso", "--verdade", str(verdade),
                  "--classes", str(classes),
                  "--sem-correcoes", "--limiares", "0.01", "0.05", "0.2", "--json", str(destino)])
    r = json.loads(destino.read_text())
    assert (r["imagens"], r["objetos"]) == (2, 3)
    assert r["sem_rotulo"] == ["val_c.jpg"] and r["fora_das_classes"] == {"Pilha": 1}
    assert r["limiares_abaixo_do_piso"] == [0.01]
    assert r["cobertura"]["0.2"] == pytest.approx({
        "cobertura": 2 / 3, "completas": 0.5, "caixas_por_imagem": 1.0,
        "sobra_por_imagem": 0.0, "classe_certa": 0.5, "material_certo": 0.5})
    assert r["cobertura"]["0.05"] == pytest.approx({
        "cobertura": 1.0, "completas": 1.0, "caixas_por_imagem": 2.0,
        "sobra_por_imagem": 0.5, "classe_certa": 2 / 3, "material_certo": 2 / 3})
    assert r["deteccao"]["0.2"] == pytest.approx({
        "acertos": 1, "falsos_positivos": 1, "falsos_negativos": 2,
        "precisao": 0.5, "recall": 1 / 3})
    assert r["confusao"] == [{"verdadeira": "Garrafa", "prevista": "Garrafa", "n": 1},
                             {"verdadeira": "Lata", "prevista": "Garrafa", "n": 1},
                             {"verdadeira": "Lata", "prevista": "sem caixa", "n": 1}]
    assert r["faixas"]["0.05-0.15"] == {"caixas": 2, "cobrem": 1, "classe_certa": 1}
    assert r["faixas"]["0.3-0.35"] == {"caixas": 1, "cobrem": 1, "classe_certa": 0}
    assert r["clique"] == {"sem_caixa": 1, "primeira": 1, "tres_primeiras": 1,
                           "candidatas_por_imagem": 1.0}


def test_avaliar_sem_nenhuma_imagem_com_rotulo(tmp_path):
    verdade = tmp_path / "v"
    dataset(verdade, {"a.jpg": []})
    saida = tmp_path / "saida"
    importar.importar(saida, [verdade / "images" / "a.jpg"], "val", ["Garrafa"])
    with pytest.raises(ValueError, match="nenhuma imagem"):
        avaliar.avaliar(saida, "falso", CLASSES, [verdade], {}, [0.2])


def test_medir_erro_conjunto_compara_com_o_esperado_por_classe():
    caixa = [(0.1 * i, 0.1, 0.1 * i + 0.05, 0.2) for i in range(5)]
    # 5 objetos da classe 0 (Drink can); materiais: 0 metal, 1 plastic
    verdade = [(0, c) for c in caixa]
    proposta = {"parametros": {"confianca": 0.2}}

    def pares(classes, confs=None):
        confs = confs or [0.9] * len(classes)
        return [("foto.jpg", proposta,
                 [(k, conf, c) for k, conf, c in zip(classes, confs, caixa)], verdade)]

    # a erra os objetos 0 e 1 (classe 1), b erra 0 (classe 1) e 2 ("outra", fora de
    # classes.yaml); o objeto 4 de b está abaixo do limiar: fica de fora
    a = pares([1, 1, 0, 0, 0])
    b = pares([1, 0, None, 0, 0], [0.9, 0.9, 0.9, 0.9, 0.1])
    r = avaliar.medir_erro_conjunto(a, b, ["metal", "plastic"])
    assert r["objetos"] == 4 and r["imagens"] == 1
    assert (r["erro_a"], r["erro_b"], r["ambos_erram"]) == (2, 2, 1)
    assert r["esperado_ambos_erram"] == pytest.approx(2 * 2 / 4)
    assert (r["concordam"], r["concordam_errado"]) == (2, 1)
    assert r["esperado_concordam_errado"] == pytest.approx(2 * 1 / 4)   # só a classe 1
    assert r["material_concordam_errado"] == 1
    assert r["_erros_iguais"] == Counter({(0, 1): 1})
    assert r["phi"] == pytest.approx(0.0)   # 1 de 2 erros em comum, com 2 de 4: independentes
    # com o limiar de b mais baixo, o objeto 4 entra (acerto dos dois)
    assert avaliar.medir_erro_conjunto(a, b, ["metal", "plastic"], 0.2, 0.05)["objetos"] == 5
    # imagens sem proposta do outro anotador não entram
    assert avaliar.medir_erro_conjunto(a, [], ["metal", "plastic"])["objetos"] == 0


def test_medir_voto_corretas_por_inteiro():
    caixa = [(0.1, 0.1, 0.3, 0.3), (0.5, 0.5, 0.7, 0.7)]
    verdade = [(0, caixa[0]), (1, caixa[1])]
    proposta = {"parametros": {"confianca": 0.2}}

    def pares(nome, classes, conf=0.9):
        return (nome, proposta, [(k, conf, c) for k, c in zip(classes, caixa)], verdade)

    a = [pares("ok.jpg", [0, 1]), pares("errada.jpg", [0, 0]), pares("baixa.jpg", [0, 1], 0.1)]
    b = [pares("ok.jpg", [0, 1]), pares("errada.jpg", [0, 0]), pares("baixa.jpg", [0, 1])]
    r = avaliar.medir_voto([a, b], [None, None], ["metal", "metal"])
    # baixa.jpg: a está abaixo do limiar gravado (0,2), não acha nada
    assert (r["imagens"], r["aprovadas"], r["reprovada_quantidade"]) == (3, 2, 1)
    assert (r["corretas"], r["corretas_material"]) == (1, 2)
    assert (r["caixas_aprovadas"], r["caixas_certas"]) == (4, 3)
    assert r["_erros"] == Counter({(1, 0): 1})
    # por caixa: ok (2 certas), errada (2, uma certa), baixa (a sem caixa: nenhuma)
    assert (r["caixas_consenso"], r["caixas_consenso_certas"]) == (4, 3)
    assert r["objetos_com_consenso"] == 4
    # com o limiar de a em 0,05, baixa.jpg passa
    assert avaliar.medir_voto([a, b], [0.05, None], ["metal", "metal"])["aprovadas"] == 3
