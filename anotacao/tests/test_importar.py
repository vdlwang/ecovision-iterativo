"""Testes do importar.py."""

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import importar  # noqa: E402
import saida as formato  # noqa: E402

NOMES = ["Garrafa", "Lata"]


def foto(pasta, nome, tamanho=(40, 20), orientacao=None, horario=None, subseg=None, fuso=None):
    """horario: 'AAAA:MM:DD hh:mm:ss' no DateTimeOriginal, com subseg e fuso opcionais."""
    caminho = pasta / nome
    pasta.mkdir(parents=True, exist_ok=True)
    exif = Image.Exif()
    if orientacao:
        exif[importar.TAG_ORIENTACAO_EXIF] = orientacao
    if horario:
        ifd = exif.get_ifd(importar.TAG_IFD_EXIF)
        ifd[importar.TAG_DATETIME_ORIGINAL] = horario
        if subseg:
            ifd[importar.TAG_SUBSEC_TIME_ORIGINAL] = subseg
        if fuso:
            ifd[importar.TAG_OFFSET_TIME_ORIGINAL] = fuso
    Image.new("RGB", tamanho, (200, 30, 30)).save(caminho, exif=exif)
    return caminho


def test_importa_copia_registra_e_pula_as_ja_importadas(tmp_path):
    fotos = [foto(tmp_path / "f", "a.jpg"), foto(tmp_path / "f", "b.png")]
    saida = tmp_path / "saida"
    r = importar.importar(saida, fotos, "l1", NOMES, conjunto="teste", agora="2026-11-11")
    assert r == {"importadas": ["l1_a.jpg", "l1_b.png"], "puladas": [],
                 "conjuntos": {"treino": 0, "teste": 2}, "sem_horario": 2, "proximas": [],
                 "avisos": []}
    # cópia byte a byte: nada foi regravado
    assert (saida / "images" / "l1_a.jpg").read_bytes() == fotos[0].read_bytes()
    estado = formato.ler_estado(saida)
    assert [(n, l["status"], l["lote"], l["conjunto"], l["largura"], l["altura"])
            for n, l in estado.items()] == [("l1_a.jpg", "pendente", "l1", "teste", 40, 20),
                                            ("l1_b.png", "pendente", "l1", "teste", 40, 20)]
    assert formato.ler_lotes(saida) == {"l1": {"regiao": None, "importado_em": "2026-11-11"}}
    assert yaml.safe_load((saida / "data.yaml").read_text())["names"] == {0: "Garrafa", 1: "Lata"}

    # De novo, com uma nova e outro conjunto: as antigas são puladas e não mudam de
    # conjunto; a nova recebe o pedido (o conjunto é de cada imagem, não do lote)
    fotos.append(foto(tmp_path / "f", "c.jpg"))
    r = importar.importar(saida, fotos, "l1", NOMES, conjunto="treino")
    assert r["importadas"] == ["l1_c.jpg"] and r["puladas"] == ["l1_a.jpg", "l1_b.png"]
    assert r["conjuntos"] == {"treino": 1, "teste": 0}
    assert {n: l["conjunto"] for n, l in formato.ler_estado(saida).items()} == {
        "l1_a.jpg": "teste", "l1_b.png": "teste", "l1_c.jpg": "treino"}


def test_outro_lote_mesma_foto_nao_colide(tmp_path):
    a = foto(tmp_path / "f", "a.jpg")
    saida = tmp_path / "saida"
    importar.importar(saida, [a], "l1", NOMES, conjunto="treino")
    importar.importar(saida, [a], "l2", NOMES, conjunto="teste")
    linhas = formato.ler_estado(saida)
    assert {n: l["conjunto"] for n, l in linhas.items()} == {"l1_a.jpg": "treino",
                                                             "l2_a.jpg": "teste"}


def test_recusas(tmp_path):
    a = foto(tmp_path / "f", "a.jpg")
    saida = tmp_path / "saida"
    for lote in ("l_1", "", "-l", "l/1"):
        with pytest.raises(ValueError, match="lote inválido"):
            importar.importar(saida, [a], lote, NOMES)
    with pytest.raises(ValueError, match="repetidos"):
        importar.importar(saida, [a, foto(tmp_path / "g", "a.jpg")], "l1", NOMES)
    for regiao in ([0, 0, 1.2, 1], [0.5, 0, 0.4, 1], [0, 0.5, 1, 0.5]):
        with pytest.raises(ValueError, match="região"):
            importar.importar(saida, [a], "l1", NOMES, regiao=regiao)
    with pytest.raises(ValueError, match="conjunto"):
        importar.importar(saida, [a], "l1", NOMES, conjunto="validacao")
    importar.importar(saida, [a], "l1", NOMES, regiao=[0, 0.1, 1, 0.9])
    with pytest.raises(ValueError, match="região"):
        importar.importar(saida, [a], "l1", NOMES, regiao=[0, 0, 1, 1])


def test_registra_o_tamanho_depois_do_giro_e_recusa_colisao_antes_de_copiar(tmp_path):
    saida = tmp_path / "saida"
    importar.importar(saida, [foto(tmp_path / "f", "g.jpg", (40, 20), orientacao=6)], "l1",
                      NOMES)
    assert formato.ler_estado(saida)["l1_g.jpg"]["largura"] == 20
    with pytest.raises(ValueError, match="colide"):
        importar.importar(saida, [foto(tmp_path / "f", "g.png")], "l1", NOMES)
    assert not (saida / "images" / "l1_g.png").exists()


def test_regrava_so_a_girada_ou_grande(tmp_path):
    girada = foto(tmp_path / "f", "g.jpg", (40, 20), orientacao=6)  # girar 90°
    grande = foto(tmp_path / "f", "G.png", (400, 100))
    destino = tmp_path / "d"
    destino.mkdir()
    assert importar.gravar_imagem(girada, destino / "g.jpg") == "regravada"
    with Image.open(destino / "g.jpg") as imagem:
        assert imagem.size == (20, 40)
        assert imagem.getexif().get(importar.TAG_ORIENTACAO_EXIF, 1) == 1
    assert importar.gravar_imagem(grande, destino / "G.png") == "copia"
    assert importar.gravar_imagem(grande, destino / "G.png", lado_maximo=200) == "regravada"
    with Image.open(destino / "G.png") as imagem:
        assert imagem.size == (200, 50)


def test_link_quando_nao_regrava(tmp_path):
    a = foto(tmp_path / "f", "a.jpg")
    saida = tmp_path / "saida"
    importar.importar(saida, [a], "l1", NOMES, link=True)
    gravada = saida / "images" / "l1_a.jpg"
    assert gravada.read_bytes() == a.read_bytes()
    assert os.path.samefile(gravada, a)


def test_sorteio_por_imagem_estavel_e_perto_de_um_em_dez():
    assert importar.sortear_conjunto("l1_a.jpg") == importar.sortear_conjunto("l1_a.jpg")
    testes = sum(importar.sortear_conjunto(f"l1_foto-{i}.jpg") == "teste" for i in range(2000))
    assert 150 <= testes <= 250  # 1 em 10 de 2000 = 200


def test_sorteio_mistura_os_conjuntos_num_lote(tmp_path):
    fotos = [foto(tmp_path / "f", f"{i:02d}.jpg") for i in range(40)]
    saida = tmp_path / "saida"
    r = importar.importar(saida, fotos, "l1", NOMES)
    esperado = {c: sum(importar.sortear_conjunto(f"l1_{i:02d}.jpg") == c for i in range(40))
                for c in importar.CONJUNTOS}
    assert r["conjuntos"] == esperado and esperado["teste"] and esperado["treino"]
    assert all(l["conjunto"] == importar.sortear_conjunto(n)
               for n, l in formato.ler_estado(saida).items())


def test_main_com_pasta(tmp_path, capsys):
    foto(tmp_path / "f", "a.jpg")
    foto(tmp_path / "f", "b.jpg")
    (tmp_path / "f" / "leia.txt").write_text("não é imagem")
    saida = tmp_path / "saida"
    importar.main([str(tmp_path / "f"), "-o", str(saida), "--lote", "l1", "--regiao",
                   "0", "0.1", "1", "0.9"])
    assert "2 imagem(ns) importada(s) (" in capsys.readouterr().out
    assert formato.ler_lotes(saida)["l1"]["regiao"] == [0.0, 0.1, 1.0, 0.9]
    with pytest.raises(SystemExit):
        importar.main([str(tmp_path / "f"), "-o", str(saida)])  # sem --lote


UTC = timezone.utc


def t(segundos):
    return datetime(2026, 11, 15, 12, 0, tzinfo=UTC) + timedelta(seconds=segundos)


def test_horario_do_exif_com_fracao_e_fuso_e_regravacao(tmp_path):
    # o formato que o backend grava (backend/captura.py): UTC com milissegundos
    a = foto(tmp_path / "f", "a.jpg", horario="2026:11:15 23:29:03", subseg="146", fuso="+00:00")
    assert importar.horario_captura(a) == datetime(2026, 11, 15, 23, 29, 3, 146000, tzinfo=UTC)
    b = foto(tmp_path / "f", "b.jpg", horario="2025:03:23 18:17:56", fuso="-03:00")
    assert importar.horario_captura(b) == datetime(2025, 3, 23, 21, 17, 56, tzinfo=UTC)
    # sem fuso: hora local da máquina
    c = foto(tmp_path / "f", "c.jpg", horario="2025:03:23 18:17:56")
    assert importar.horario_captura(c) == datetime(2025, 3, 23, 18, 17, 56).astimezone(UTC)
    # girada: o horário vem da origem, mesmo que a regravação descarte o EXIF
    g = foto(tmp_path / "f", "g.jpg", orientacao=6, horario="2026:11:15 23:29:03", fuso="+00:00")
    saida = tmp_path / "saida"
    importar.importar(saida, [g], "l1", NOMES)
    assert formato.ler_estado(saida)["l1_g.jpg"]["capturada_em"] == "2026-11-15T23:29:03+00:00"


def test_horario_pelo_nome_e_sem_horario(tmp_path):
    # as fotos de legado/database perderam o EXIF, mas o nome tem o horário
    n = foto(tmp_path / "f", "20250503_140329.jpg")
    assert importar.horario_captura(n) == datetime(2025, 5, 3, 14, 3, 29).astimezone(UTC)
    assert importar.horario_nome("IMG_20250503_140329_1.jpg") is not None
    for nome in ("a.jpg", "120250503_140329.jpg", "20251303_140329.jpg", "20250503_1403.jpg"):
        assert importar.horario_nome(nome) is None, nome
    # EXIF vence o nome; EXIF inválido cai no nome
    e = foto(tmp_path / "f", "20250503_140329b.jpg", horario="2026:11:15 23:29:03", fuso="+00:00")
    assert importar.horario_captura(e) == datetime(2026, 11, 15, 23, 29, 3, tzinfo=UTC)
    x = foto(tmp_path / "g", "20250503_140329.jpg", horario="lixo")
    assert importar.horario_captura(x) == importar.horario_captura(n)
    assert importar.horario_captura(foto(tmp_path / "f", "a.jpg")) is None


def test_agrupa_em_cadeia_e_sorteia_pela_primeira():
    # 0, 5, 12: cadeia (cada uma a menos de 10 s da anterior); 30 sozinha; sem horário à parte
    novas = [("l_c", t(12)), ("l_a", t(0)), ("l_b", t(5)), ("l_d", t(30)), ("l_e", None)]
    conjuntos, proximas, avisos = importar.agrupar_por_horario(novas, [], 10)
    assert proximas == [["l_a", "l_b", "l_c"]] and avisos == []
    primeira = importar.sortear_conjunto("l_a")
    assert {n: conjuntos[n] for n in ("l_a", "l_b", "l_c")} == dict.fromkeys(
        ("l_a", "l_b", "l_c"), primeira)
    assert conjuntos["l_d"] == importar.sortear_conjunto("l_d")
    assert conjuntos["l_e"] == importar.sortear_conjunto("l_e")
    # exatamente Δ não é "a menos de Δ"; janela 0 desliga
    assert importar.agrupar_por_horario([("x", t(0)), ("y", t(10))], [], 10)[1] == []
    assert importar.agrupar_por_horario([("x", t(0)), ("y", t(0))], [], 0)[1] == []


def test_grupo_herda_o_conjunto_das_ja_importadas():
    def nome_de(conjunto):  # um nome que o sorteio põe no conjunto dado
        return next(f"n{i}" for i in range(1000) if importar.sortear_conjunto(f"n{i}") == conjunto)
    # a nova antes da já importada também herda (o grupo não depende da ordem)
    novo = nome_de("treino")
    conjuntos, proximas, avisos = importar.agrupar_por_horario(
        [(novo, t(0))], [("velha", t(4), "teste")], 10)
    assert conjuntos == {novo: "teste"} and proximas == [[novo, "velha"]] and avisos == []
    # grupo já misturado: a mais próxima no tempo decide, e há aviso
    conjuntos, _, avisos = importar.agrupar_por_horario(
        [("n", t(7))], [("v1", t(0), "treino"), ("v2", t(9), "teste")], 10)
    assert conjuntos == {"n": "teste"} and len(avisos) == 1 and "v1 (treino)" in avisos[0]
    # grupo só de já importadas não aparece
    assert importar.agrupar_por_horario([], [("v1", t(0), "treino"), ("v2", t(1), "teste")],
                                        10) == ({}, [], [])
    # --conjunto vence, com aviso se contradiz uma vizinha
    conjuntos, _, avisos = importar.agrupar_por_horario(
        [(nome_de("teste"), t(0))], [("velha", t(3), "treino")], 10, conjunto="teste")
    assert list(conjuntos.values()) == ["teste"] and len(avisos) == 1


def test_importar_confere_a_janela_entre_lotes(tmp_path, capsys):
    """
    Os 4 cenários de legado/database: as mesmas cenas, 6-7 s de diferença, em
    lotes; com --janela 10, porque o padrão (4 s, o da captura) não os liga.
    """
    cenarios = {"0SF": "140322", "0CF": "140329", "45CF": "140335", "45SF": "140342"}
    saida = tmp_path / "saida"
    for i, (lote, hora) in enumerate(cenarios.items()):
        pasta = tmp_path / lote
        foto(pasta, f"20250503_{hora}.jpg")
        foto(pasta, f"20250503_15{i}000.jpg")  # outra cena, longe das demais
        importar.main([str(pasta), "-o", str(saida), "--lote", lote, "--janela", "10"])
    estado = formato.ler_estado(saida)
    mesma_cena = {estado[f"{lote}_20250503_{hora}.jpg"]["conjunto"]
                  for lote, hora in cenarios.items()}
    assert mesma_cena == {estado["0SF_20250503_140322.jpg"]["conjunto"]}
    assert all(r["capturada_em"] for r in estado.values())
    saida_texto = capsys.readouterr().out
    assert saida_texto.count("1 grupo(s)") == 3 and "Aviso" not in saida_texto
    # --janela 0: nada se agrupa
    pasta = tmp_path / "outro"
    foto(pasta, "20250503_140323.jpg")
    r = importar.importar(saida, [pasta / "20250503_140323.jpg"], "l9", NOMES, janela=0)
    assert r["proximas"] == []
    with pytest.raises(ValueError, match="janela"):
        importar.importar(saida, [pasta / "20250503_140323.jpg"], "l9", NOMES, janela=-1)
