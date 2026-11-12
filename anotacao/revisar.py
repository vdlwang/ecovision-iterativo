"""
Servidor local da página de revisão das anotações (PLANO-REVISAO.md, seção 3).

Serve revisar.html e uma API JSON sobre um diretório gerado pelo anotar.py.
Lê o disco a cada requisição, então mudanças feitas à mão aparecem sem
reiniciar. Escuta só em 127.0.0.1.

    GET /                          a página
    GET /api/classes               [{id, nome, material, atalho}]
    GET /api/imagens?status=&ordem= fila, anotadores e contagem por status
    GET /api/imagens/<nome>        propostas, anotação final, status e revisão
    PUT /api/imagens/<nome>        salva ou descarta uma pendente (saida.revisar)
    GET /images/<arquivo>          a imagem

Uso:
    python anotacao/revisar.py anotacoes [--porta 8000] [--abrir]
"""

import argparse
import json
import mimetypes
import sys
import threading
import webbrowser
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

import saida as formato
from anotar import DIR_SCRIPT, carregar_classes

PAGINA = DIR_SCRIPT / "revisar.html"
FILTROS = (*formato.STATUS, "todas")
ORDENS = ("incerteza", "nome")
TAMANHO_MAXIMO_PEDIDO = 1 << 20


class ErroHTTP(Exception):
    def __init__(self, status, mensagem):
        super().__init__(mensagem)
        self.status = status


def listar_classes(saida, classes):
    """
    Classes do data.yaml. As que o anotador procura (classes.yaml) trazem o
    material e o atalho, a posição delas na lista (1..), que a página usa nas
    teclas 1-9 e no topo da busca; as outras, None.
    """
    do_anotador = {c["nome"]: (k, c["material"]) for k, c in enumerate(classes, 1)}
    return [{"id": i, "nome": n, "material": do_anotador.get(n, (None, None))[1],
             "atalho": do_anotador.get(n, (None, None))[0]}
            for i, n in sorted(formato.nomes_classes(saida).items())]


def resumir(dados):
    """Linha da fila a partir de saida.ler_imagem."""
    confiancas = [c["conf"] for caixas in dados["propostas"].values() for c in caixas]
    return {
        "nome": dados["nome"],
        "status": dados["status"],
        "anotadores": sorted(dados["propostas"]),
        "n_caixas": {a: len(c) for a, c in dados["propostas"].items()},
        "confianca_min": min(confiancas) if confiancas else None,
        "tem_final": dados["final"] is not None,
    }


def montar_fila(saida, status="pendente", ordem="incerteza"):
    """
    Imagens do imagens.csv com o status pedido. Ordem 'incerteza' (RF10): menor
    confiança entre as caixas propostas, crescente; imagens sem nenhuma caixa
    proposta vêm antes, porque são as que mais podem ter objeto não achado.
    """
    if status not in FILTROS:
        raise ErroHTTP(HTTPStatus.BAD_REQUEST, f"status deve ser um de {', '.join(FILTROS)}")
    if ordem not in ORDENS:
        raise ErroHTTP(HTTPStatus.BAD_REQUEST, f"ordem deve ser uma de {', '.join(ORDENS)}")
    nomes = formato.nomes_classes(saida)
    anotadores = formato.anotadores(saida)
    _, estado = formato.ler_estado(saida)
    contagem = {s: 0 for s in formato.STATUS}
    fila = []
    for nome, linha in estado.items():
        contagem[linha["status"]] = contagem.get(linha["status"], 0) + 1
        if status == "todas" or linha["status"] == status:
            fila.append(resumir(formato.ler_imagem(saida, nome, nomes, anotadores, linha)))
    if ordem == "incerteza":
        fila.sort(key=lambda i: (i["confianca_min"] is not None, i["confianca_min"] or 0))
    else:
        fila.sort(key=lambda i: i["nome"])
    return {"imagens": fila, "anotadores": anotadores, "contagem": contagem}


def nome_valido(saida, bruto):
    """
    Nome de imagem vindo da URL: precisa estar no imagens.csv, o que já impede
    caminhos para fora da saída; barras e '..' nem chegam a ser procurados.
    """
    nome = unquote(bruto)
    _, estado = formato.ler_estado(saida)
    if not nome or "/" in nome or "\\" in nome or nome.startswith(".") or nome not in estado:
        raise ErroHTTP(HTTPStatus.NOT_FOUND, f"imagem '{nome}' não está no imagens.csv")
    return nome, estado[nome]


def detalhar(saida, bruto):
    nome, linha = nome_valido(saida, bruto)
    dados = formato.ler_imagem(saida, nome, formato.nomes_classes(saida),
                               formato.anotadores(saida), linha, com_candidatas=True)
    caminho = Path(saida) / "images" / nome
    if not caminho.is_file():
        raise ErroHTTP(HTTPStatus.NOT_FOUND, f"{caminho} não existe")
    dados["largura"], dados["altura"] = formato.tamanho_imagem(caminho)
    dados["revisao"] = formato.ler_revisao(saida, nome)
    return dados


def criar_servidor(saida, classes, host="127.0.0.1", porta=8000):
    """Servidor pronto para serve_forever(); porta 0 escolhe uma livre (testes)."""
    saida = Path(saida)
    trava = threading.Lock()  # uma gravação por vez

    class Tratador(BaseHTTPRequestHandler):
        def do_GET(self):
            url = urlsplit(self.path)
            consulta = {k: v[-1] for k, v in parse_qs(url.query).items()}
            try:
                if url.path in ("/", "/index.html"):
                    self.enviar(PAGINA.read_bytes(), "text/html; charset=utf-8")
                elif url.path == "/api/classes":
                    self.enviar_json(listar_classes(saida, classes))
                elif url.path == "/api/imagens":
                    self.enviar_json(montar_fila(saida, consulta.get("status", "pendente"),
                                                 consulta.get("ordem", "incerteza")))
                elif url.path.startswith("/api/imagens/"):
                    self.enviar_json(detalhar(saida, url.path[len("/api/imagens/"):]))
                elif url.path.startswith("/images/"):
                    nome, _ = nome_valido(saida, url.path[len("/images/"):])
                    caminho = saida / "images" / nome
                    if not caminho.is_file():
                        raise ErroHTTP(HTTPStatus.NOT_FOUND, f"{caminho} não existe")
                    tipo = mimetypes.guess_type(nome)[0] or "application/octet-stream"
                    self.enviar(caminho.read_bytes(), tipo, cache=True)
                else:
                    raise ErroHTTP(HTTPStatus.NOT_FOUND, f"rota {url.path} não existe")
            except ErroHTTP as erro:
                self.enviar_json({"erro": str(erro)}, erro.status)
            except ValueError as erro:  # arquivo da saída inválido
                self.enviar_json({"erro": str(erro)}, HTTPStatus.INTERNAL_SERVER_ERROR)

        def do_PUT(self):
            url = urlsplit(self.path)
            try:
                # Um site aberto no navegador não deve conseguir gravar aqui
                # (DNS rebinding): só aceita o próprio endereço local
                host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
                if host not in ("127.0.0.1", "localhost"):
                    raise ErroHTTP(HTTPStatus.FORBIDDEN, f"Host {host!r} não aceito")
                if not url.path.startswith("/api/imagens/"):
                    raise ErroHTTP(HTTPStatus.NOT_FOUND, f"rota {url.path} não existe")
                if not (self.headers.get("Content-Type") or "").startswith("application/json"):
                    raise ErroHTTP(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "envie application/json")
                tamanho = int(self.headers.get("Content-Length") or 0)
                if not 0 < tamanho <= TAMANHO_MAXIMO_PEDIDO:
                    raise ErroHTTP(HTTPStatus.BAD_REQUEST, "corpo vazio ou grande demais")
                try:
                    pedido = json.loads(self.rfile.read(tamanho))
                except ValueError:
                    raise ErroHTTP(HTTPStatus.BAD_REQUEST, "corpo não é JSON") from None
                nome, _ = nome_valido(saida, url.path[len("/api/imagens/"):])
                with trava:
                    formato.revisar(saida, nome, pedido,
                                    datetime.now().astimezone().isoformat(timespec="seconds"))
                self.enviar_json(detalhar(saida, url.path[len("/api/imagens/"):]))
            except ErroHTTP as erro:
                self.enviar_json({"erro": str(erro)}, erro.status)
            except formato.RevisaoInvalida as erro:
                self.enviar_json({"erro": str(erro)}, erro.status)
            except ValueError as erro:
                self.enviar_json({"erro": str(erro)}, HTTPStatus.INTERNAL_SERVER_ERROR)

        def enviar(self, corpo, tipo, status=HTTPStatus.OK, cache=False):
            self.send_response(status)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(corpo)))
            self.send_header("Cache-Control", "max-age=60" if cache else "no-store")
            self.end_headers()
            self.wfile.write(corpo)

        def enviar_json(self, dados, status=HTTPStatus.OK):
            self.enviar(json.dumps(dados, ensure_ascii=False).encode("utf-8"),
                        "application/json; charset=utf-8", status)

        def log_request(self, code="-", size="-"):
            if isinstance(code, int) and code >= 400:  # só os erros
                super().log_request(code, size)

    return ThreadingHTTPServer((host, porta), Tratador)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Página local de revisão das anotações.")
    parser.add_argument("saida", type=Path, nargs="?", default=Path("anotacoes"),
                        help="diretório gerado pelo anotar.py (padrão: ./anotacoes)")
    parser.add_argument("--classes", type=Path, default=DIR_SCRIPT / "classes.yaml",
                        help="lista de classes, para o material (padrão: anotacao/classes.yaml)")
    parser.add_argument("--porta", type=int, default=8000, help="porta local (padrão: 8000)")
    parser.add_argument("--abrir", action="store_true", help="abre a página no navegador")
    args = parser.parse_args(argv)

    if not (args.saida / "imagens.csv").exists():
        raise ValueError(f"{args.saida / 'imagens.csv'} não existe: rode o anotar.py antes "
                         "(saídas do formato antigo, só com labels/, não servem)")
    formato.nomes_classes(args.saida)  # confere o data.yaml antes de subir
    servidor = criar_servidor(args.saida, carregar_classes(args.classes), porta=args.porta)
    url = f"http://127.0.0.1:{servidor.server_address[1]}/"
    print(f"Revisão de {args.saida.resolve()} em {url} (Ctrl+C para sair)")
    if args.abrir:
        webbrowser.open(url)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()


if __name__ == "__main__":
    try:
        main()
    except ValueError as erro:
        sys.exit(f"Erro: {erro}")
