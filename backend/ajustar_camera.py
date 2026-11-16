"""
Calibração da câmera (etapa 6b do backend/PLANO-CAPTURA.md). Rode com o
backend parado: a câmera só abre num programa por vez.

    python ajustar_camera.py                          # aplica o bloco camera do config.json,
                                                      # mostra o lido de volta e grava uma amostra
    python ajustar_camera.py --listar                 # formatos e resoluções, com o fps medido
    python ajustar_camera.py --varrer exposicao 100 200 400 800
    python ajustar_camera.py --varrer temperatura_cor 3500 4500 5500
    python ajustar_camera.py --varrer saturacao 256 384 511

Os quadros vão para capturas/ajuste/<horário>/, com o valor no nome. A
varredura parte do bloco camera do config.json e muda só o campo varrido.
No Linux, o driver guarda o último valor posto até a câmera ser desconectada;
o backend reaplica o config.json a cada abertura, então isso não o afeta.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2

import camera
from captura import carimbo

BACKEND_DIR = Path(__file__).parent
CONFIG_FILE = BACKEND_DIR / "config.json"
PASTA_AJUSTE = BACKEND_DIR / "capturas" / "ajuste"

CAMPOS_VARRIVEIS = ("exposicao", "temperatura_cor", "foco", "ganho",
                    "brilho", "contraste", "saturacao", "nitidez", "gama")
RESOLUCOES_COMUNS = [(640, 480), (800, 600), (1280, 720), (1920, 1080)]
ACOMODAR_S = 1.0  # quadros descartados depois de mudar um valor (a exposição demora a assentar)
MEDIR_FPS_S = 3.0


def ler_config():
    cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8")) if CONFIG_FILE.exists() else {}
    return cfg.get("camera_index", 0), camera.completar_config(cfg.get("camera"))


def descartar(cap, segundos):
    fim = time.monotonic() + segundos
    quadro = None
    while time.monotonic() < fim:
        ok, q = cap.read()
        if ok:
            quadro = q
    return quadro


def medir_fps(cap, segundos=MEDIR_FPS_S):
    descartar(cap, 0.5)
    n, inicio = 0, time.monotonic()
    while time.monotonic() - inicio < segundos:
        n += cap.read()[0]
    return n / (time.monotonic() - inicio)


def formatos_v4l2(indice):
    """[(fourcc, largura, altura)] pelo v4l2-ctl; None se não há como saber."""
    if not shutil.which("v4l2-ctl") or not isinstance(indice, int):
        return None
    saida = subprocess.run(["v4l2-ctl", "-d", f"/dev/video{indice}", "--list-formats-ext"],
                           capture_output=True, text=True).stdout
    formatos, atual = [], None
    for linha in saida.splitlines():
        m = re.search(r"'(\w{4})'", linha)
        if m and "[" in linha:
            atual = m.group(1)
        m = re.search(r"Size: Discrete (\d+)x(\d+)", linha)
        if m and atual:
            formatos.append((atual, int(m.group(1)), int(m.group(2))))
    return formatos or None


def pasta_saida():
    pasta = PASTA_AJUSTE / carimbo(datetime.now(timezone.utc)).split(".")[0]
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def mostrar(relatorio):
    print(camera.descrever(relatorio))
    for nome, valor in relatorio["lido"].items():
        print(f"  {nome:22s} lido {valor}")
    for d in relatorio["divergencias"]:
        print(f"  DIVERGE {d['campo']}: pedido {d['pedido']}, lido {d['lido']}")


def listar(indice, cfg):
    formatos = formatos_v4l2(camera.normalizar_fonte(indice))
    if formatos is None:
        print("v4l2-ctl indisponível: testando resoluções comuns em MJPG e YUYV")
        formatos = [(f, w, h) for f in ("MJPG", "YUYV") for w, h in RESOLUCOES_COMUNS]
    print(f"{'pedido':>18s}  {'entregue':>18s}  fps medido")
    for fourcc, w, h in formatos:
        pedido = {**cfg, "fourcc": fourcc, "largura": w, "altura": h, "fps": None}
        cap, rel = camera.abrir(indice, pedido)
        try:
            fps = medir_fps(cap)
        finally:
            cap.release()
        e = rel["efetivo"]
        print(f"{fourcc} {w:>5d}x{h:<5d}  {e['fourcc'] or '?'} {e['largura']:>5d}x{e['altura']:<5d}"
              f"  {fps:5.1f}")
    print("O fps medido cai com a exposição automática em pouca luz.")


def varrer(indice, cfg, campo, valores):
    cap, rel = camera.abrir(indice, cfg)
    mostrar(rel)
    pasta = pasta_saida()
    try:
        for valor in valores:
            pedido = camera.propriedades({**cfg, campo: valor}, rel["backend"])
            pares = [p for p in pedido if p[0] in (campo, campo + "_auto")]
            for nome, prop, v in pares:
                cap.set(prop, v)
            lido = cap.get(next(p for n, p, _v in pares if n == campo))
            quadro = descartar(cap, ACOMODAR_S)
            if quadro is None:
                print(f"{campo}={valor}: sem quadro")
                continue
            arquivo = pasta / f"{campo}_{valor}.jpg"
            cv2.imwrite(str(arquivo), quadro)
            print(f"{campo}={valor}: lido {lido}, brilho médio {quadro.mean():.0f}, {arquivo.name}")
    finally:
        cap.release()
    print(f"Quadros em {pasta}")


def amostra(indice, cfg):
    cap, rel = camera.abrir(indice, cfg)
    try:
        mostrar(rel)
        print(f"  fps medido {medir_fps(cap):.1f}")
        quadro = descartar(cap, ACOMODAR_S)
    finally:
        cap.release()
    if quadro is not None:
        arquivo = pasta_saida() / "amostra.jpg"
        cv2.imwrite(str(arquivo), quadro)
        print(f"Amostra em {arquivo}")
    return 1 if rel["divergencias"] else 0


def main():
    parser = argparse.ArgumentParser(description="Calibração da câmera (bloco camera do config.json)")
    parser.add_argument("--camera", help="índice ou URL; padrão: camera_index do config.json")
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--listar", action="store_true", help="formatos e resoluções, com o fps medido")
    grupo.add_argument("--varrer", nargs="+", metavar=("CAMPO", "VALOR"),
                       help=f"grava um quadro por valor; CAMPO: {', '.join(CAMPOS_VARRIVEIS)}")
    args = parser.parse_args()

    indice, cfg = ler_config()
    if args.camera is not None:
        indice = args.camera
    indice = camera.normalizar_fonte(indice)

    if args.listar:
        listar(indice, cfg)
        return 0
    if args.varrer:
        campo, *valores = args.varrer
        if campo not in CAMPOS_VARRIVEIS or not valores:
            parser.error(f"--varrer CAMPO VALOR [VALOR ...], com CAMPO em {CAMPOS_VARRIVEIS}")
        varrer(indice, cfg, campo, [float(v) if "." in v else int(v) for v in valores])
        return 0
    return amostra(indice, cfg)


if __name__ == "__main__":
    sys.exit(main())
