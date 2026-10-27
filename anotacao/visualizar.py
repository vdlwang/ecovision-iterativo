"""
Página HTML para conferir as anotações de um diretório gerado pelo anotar.py.

Lê data.yaml, images/ e labels/ e grava <saida>/visualizar.html, que abre
direto no navegador (sem servidor): lista das imagens à esquerda, imagem com
as caixas à direita, setas do teclado para navegar. Só visualiza; não edita.

O anotar.py já gera a página ao terminar; rode este script para refazê-la
depois de mexer nos .txt à mão.

Uso:
    python anotacao/visualizar.py anotacoes
"""

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import quote

import yaml

EXTENSOES_IMAGEM = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def ler_rotulos(caminho):
    """Linhas 'id cx cy w h' de um .txt; devolve a lista e quantas linhas foram ignoradas."""
    caixas, invalidas = [], 0
    if not caminho.exists():
        return None, 0
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        partes = linha.split()
        if not partes:
            continue
        try:
            if len(partes) != 5:
                raise ValueError
            caixas.append([int(partes[0])] + [float(p) for p in partes[1:]])
        except ValueError:
            invalidas += 1
    return caixas, invalidas


def coletar(saida):
    """Classes do data.yaml e, para cada imagem, o caminho relativo e as caixas."""
    data_yaml = saida / "data.yaml"
    if not data_yaml.exists():
        raise ValueError(f"{data_yaml} não existe; é a saída do anotar.py?")
    with open(data_yaml, encoding="utf-8") as f:
        nomes = (yaml.safe_load(f) or {}).get("names") or {}
    if isinstance(nomes, list):
        nomes = dict(enumerate(nomes))

    if not (saida / "images").is_dir():
        raise ValueError(f"{saida / 'images'} não existe")
    imagens = []
    for arquivo in sorted((saida / "images").iterdir()):
        if arquivo.suffix.lower() not in EXTENSOES_IMAGEM:
            continue
        caixas, invalidas = ler_rotulos(saida / "labels" / f"{arquivo.stem}.txt")
        imagens.append({
            "nome": arquivo.name,
            "src": "images/" + quote(arquivo.name),
            "caixas": caixas or [],
            "sem_rotulo": caixas is None,
            "invalidas": invalidas,
        })
    return {str(i): n for i, n in nomes.items()}, imagens


def gerar_pagina(saida):
    """Grava <saida>/visualizar.html e devolve o caminho."""
    saida = Path(saida)
    classes, imagens = coletar(saida)
    dados = json.dumps({"classes": classes, "imagens": imagens}, ensure_ascii=False)
    # "</" fecharia a tag <script> se aparecesse num nome de arquivo
    html = PAGINA.replace("__DADOS__", dados.replace("</", "<\\/"))
    destino = saida / "visualizar.html"
    destino.write_text(html, encoding="utf-8")
    return destino


PAGINA = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Anotações</title>
<style>
  :root { --fundo: #111418; --painel: #1b2027; --borda: #2c333d; --texto: #e6e9ee;
          --suave: #9aa4b2; --destaque: #22c55e; }
  * { box-sizing: border-box; }
  body { margin: 0; font: 14px/1.4 system-ui, sans-serif; background: var(--fundo);
         color: var(--texto); display: flex; height: 100vh; }
  aside { width: 260px; flex: none; background: var(--painel); border-right: 1px solid var(--borda);
          display: flex; flex-direction: column; }
  aside header { padding: 12px 14px; border-bottom: 1px solid var(--borda); }
  aside h1 { font-size: 15px; margin: 0 0 4px; }
  aside small { color: var(--suave); }
  #lista { list-style: none; margin: 0; padding: 0; overflow-y: auto; flex: 1; }
  #lista li { padding: 8px 14px; cursor: pointer; display: flex; justify-content: space-between;
              gap: 8px; border-bottom: 1px solid var(--borda); }
  #lista li:hover { background: #232a33; }
  #lista li.atual { background: #263445; }
  #lista .nome { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  #lista .qtd { color: var(--suave); flex: none; }
  #lista .aviso { color: #f59e0b; }
  main { flex: 1; display: flex; flex-direction: column; min-width: 0; }
  .barra { display: flex; align-items: center; gap: 12px; padding: 10px 14px;
           border-bottom: 1px solid var(--borda); flex-wrap: wrap; }
  .barra button { background: var(--painel); color: var(--texto); border: 1px solid var(--borda);
                  border-radius: 6px; padding: 4px 10px; cursor: pointer; }
  .barra label { color: var(--suave); display: flex; gap: 6px; align-items: center; }
  #titulo { font-weight: 600; margin-right: auto; }
  .area { flex: 1; display: flex; align-items: center; justify-content: center;
          padding: 14px; min-height: 0; }
  .quadro { position: relative; display: inline-block; max-width: 100%; max-height: 100%; }
  .quadro img { display: block; max-width: 100%; max-height: calc(100vh - 130px); }
  .caixa { position: absolute; border: 2px solid; }
  .caixa span { position: absolute; left: -2px; bottom: 100%; padding: 1px 5px; font-size: 12px;
                color: #000; white-space: nowrap; }
  .sem-rotulos .caixa span { display: none; }
  .legenda { display: flex; flex-wrap: wrap; gap: 6px 14px; padding: 8px 14px;
             border-top: 1px solid var(--borda); color: var(--suave); min-height: 37px; }
  .legenda i { display: inline-block; width: 10px; height: 10px; margin-right: 5px; }
  @media (max-width: 700px) {
    body { flex-direction: column; height: auto; min-height: 100vh; }
    aside { width: auto; max-height: 30vh; border-right: 0; border-bottom: 1px solid var(--borda); }
    .area { padding: 14px 4px; }
    .quadro img { max-height: none; }
  }
</style>
</head>
<body>
<aside>
  <header><h1>Anotações</h1><small id="resumo"></small></header>
  <ul id="lista"></ul>
</aside>
<main>
  <div class="barra">
    <span id="titulo"></span>
    <label><input type="checkbox" id="mostrar-rotulos" checked> nomes</label>
    <label><input type="checkbox" id="mostrar-caixas" checked> caixas</label>
    <button id="anterior" title="Seta para a esquerda">&larr;</button>
    <button id="proxima" title="Seta para a direita">&rarr;</button>
  </div>
  <div class="area"><div class="quadro" id="quadro"><img id="imagem" alt=""></div></div>
  <div class="legenda" id="legenda"></div>
</main>
<script>
const DADOS = __DADOS__;
const CORES = ["#22c55e", "#3b82f6", "#f59e0b", "#ef4444", "#a855f7", "#14b8a6",
               "#ec4899", "#eab308", "#6366f1", "#f97316"];
const cor = id => CORES[id % CORES.length];
const nomeClasse = id => DADOS.classes[id] ?? `classe ${id}`;

const lista = document.getElementById("lista");
const quadro = document.getElementById("quadro");
const imagem = document.getElementById("imagem");
let atual = 0;

const totalCaixas = DADOS.imagens.reduce((s, im) => s + im.caixas.length, 0);
document.getElementById("resumo").textContent =
  `${DADOS.imagens.length} imagem(ns), ${totalCaixas} objeto(s)`;

DADOS.imagens.forEach((im, i) => {
  const li = document.createElement("li");
  const nome = document.createElement("span");
  nome.className = "nome";
  nome.textContent = im.nome;
  const qtd = document.createElement("span");
  qtd.className = "qtd" + (im.sem_rotulo || im.invalidas ? " aviso" : "");
  qtd.textContent = im.sem_rotulo ? "sem .txt" : im.caixas.length;
  li.append(nome, qtd);
  li.onclick = () => mostrar(i);
  lista.append(li);
});

function mostrar(i) {
  if (!DADOS.imagens.length) return;
  atual = (i + DADOS.imagens.length) % DADOS.imagens.length;
  const im = DADOS.imagens[atual];
  [...lista.children].forEach((li, j) => li.classList.toggle("atual", j === atual));
  lista.children[atual].scrollIntoView({ block: "nearest" });
  document.getElementById("titulo").textContent =
    `${atual + 1}/${DADOS.imagens.length} · ${im.nome}`;
  imagem.src = im.src;
  history.replaceState(null, "", `#${atual + 1}`);

  quadro.querySelectorAll(".caixa").forEach(c => c.remove());
  for (const [id, cx, cy, w, h] of im.caixas) {
    const div = document.createElement("div");
    div.className = "caixa";
    Object.assign(div.style, {
      left: `${(cx - w / 2) * 100}%`, top: `${(cy - h / 2) * 100}%`,
      width: `${w * 100}%`, height: `${h * 100}%`, borderColor: cor(id),
    });
    const span = document.createElement("span");
    span.textContent = nomeClasse(id);
    span.style.background = cor(id);
    div.append(span);
    quadro.append(div);
  }
  atualizarVisibilidade();

  const legenda = document.getElementById("legenda");
  legenda.replaceChildren();
  const contagem = {};
  im.caixas.forEach(([id]) => contagem[id] = (contagem[id] || 0) + 1);
  for (const [id, n] of Object.entries(contagem)) {
    const item = document.createElement("span");
    const amostra = document.createElement("i");
    amostra.style.background = cor(Number(id));
    item.append(amostra, `${nomeClasse(id)}: ${n}`);
    legenda.append(item);
  }
  if (im.sem_rotulo) legenda.append("Sem arquivo de rótulos em labels/.");
  else if (!im.caixas.length) legenda.append("Nenhum objeto anotado.");
  if (im.invalidas) legenda.append(` ${im.invalidas} linha(s) inválida(s) ignorada(s).`);
}

function atualizarVisibilidade() {
  const caixas = document.getElementById("mostrar-caixas").checked;
  quadro.querySelectorAll(".caixa").forEach(c => c.style.display = caixas ? "" : "none");
  quadro.classList.toggle("sem-rotulos", !document.getElementById("mostrar-rotulos").checked);
}

document.getElementById("mostrar-caixas").onchange = atualizarVisibilidade;
document.getElementById("mostrar-rotulos").onchange = atualizarVisibilidade;
document.getElementById("anterior").onclick = () => mostrar(atual - 1);
document.getElementById("proxima").onclick = () => mostrar(atual + 1);
document.addEventListener("keydown", e => {
  if (e.key === "ArrowLeft") mostrar(atual - 1);
  if (e.key === "ArrowRight") mostrar(atual + 1);
});

// #N no endereço abre a N-ésima imagem (e mantém a posição ao recarregar)
if (DADOS.imagens.length) mostrar((parseInt(location.hash.slice(1)) || 1) - 1);
else document.getElementById("titulo").textContent = "Nenhuma imagem em images/";
</script>
</body>
</html>
"""


def main(argv=None):
    parser = argparse.ArgumentParser(description="Gera a página de visualização das anotações.")
    parser.add_argument("saida", type=Path, nargs="?", default=Path("anotacoes"),
                        help="diretório gerado pelo anotar.py (padrão: ./anotacoes)")
    args = parser.parse_args(argv)
    print(f"Abra no navegador: {gerar_pagina(args.saida).resolve().as_uri()}")


if __name__ == "__main__":
    try:
        main()
    except ValueError as erro:
        sys.exit(f"Erro: {erro}")
