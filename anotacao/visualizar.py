"""
Página HTML para conferir as anotações de um diretório gerado pelo anotar.py.

Lê data.yaml, images/, labels/ (anotações finais), propostas/<anotador>/ e
imagens.csv (status), e grava <saida>/visualizar.html, que abre direto no
navegador (sem servidor): lista das imagens à esquerda, imagem com as caixas
à direita, setas do teclado para navegar. As propostas aparecem tracejadas e
com a confiança. Só visualiza; não edita.

Também serve para um diretório no formato YOLO de outra ferramenta (só
data.yaml, images/ e labels/).

O anotar.py já gera a página ao terminar; rode este script para refazê-la
depois de mexer nos arquivos à mão.

Uso:
    python anotacao/visualizar.py anotacoes
"""

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import quote

import saida as formato
from saida import EXTENSOES_IMAGEM  # noqa: F401 (usada pelo notebook do Colab)


def coletar(saida):
    """
    Classes do data.yaml, anotadores com propostas e, para cada imagem de
    images/, os dados de saida.ler_imagem.
    """
    saida = Path(saida)
    nomes = formato.nomes_classes(saida)
    if not (saida / "images").is_dir():
        raise ValueError(f"{saida / 'images'} não existe")
    _, estado = formato.ler_estado(saida)
    anotadores = formato.anotadores(saida)
    imagens = []
    for arquivo in sorted((saida / "images").iterdir()):
        if arquivo.suffix.lower() not in formato.EXTENSOES_IMAGEM:
            continue
        dados = formato.ler_imagem(saida, arquivo.name, nomes, anotadores,
                                   estado.get(arquivo.name))
        dados["src"] = "images/" + quote(arquivo.name)
        imagens.append(dados)
    return {str(i): n for i, n in nomes.items()}, anotadores, imagens


def gerar_pagina(saida):
    """Grava <saida>/visualizar.html e devolve o caminho."""
    saida = Path(saida)
    classes, anotadores, imagens = coletar(saida)
    dados = json.dumps({"classes": classes, "anotadores": anotadores, "imagens": imagens},
                       ensure_ascii=False)
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
  #lista .status { font-size: 11px; margin-left: 6px; }
  .st-pendente { color: #f59e0b; } .st-revisada { color: var(--destaque); }
  .st-descartada { color: var(--suave); text-decoration: line-through; }
  .barra select { background: var(--painel); color: var(--texto); border: 1px solid var(--borda);
                  border-radius: 6px; padding: 3px 6px; }
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
  .caixa.proposta { border-style: dashed; }
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
    <label>mostrar <select id="camada"></select></label>
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

const lista = document.getElementById("lista");
const quadro = document.getElementById("quadro");
const imagem = document.getElementById("imagem");
const seletor = document.getElementById("camada");
let atual = 0;

// Camadas: "auto" (final se houver .txt, senão a proposta do primeiro anotador
// que tiver uma), "final" ou o nome de um anotador
const CAMADAS = [["auto", "automático"], ["final", "anotação final"],
                 ...DADOS.anotadores.map(a => [a, `propostas: ${a}`])];
for (const [valor, texto] of CAMADAS) seletor.add(new Option(texto, valor));

function camada(im) {
  const escolhida = seletor.value;
  if (escolhida === "final") return { tipo: "final", caixas: im.final };
  if (escolhida !== "auto") return { tipo: escolhida, caixas: im.propostas[escolhida] ?? null };
  if (im.final || !Object.keys(im.propostas).length) return { tipo: "final", caixas: im.final };
  const a = DADOS.anotadores.find(a => im.propostas[a]);
  return { tipo: a, caixas: im.propostas[a] };
}

const porStatus = {};
DADOS.imagens.forEach(im => { if (im.status) porStatus[im.status] = (porStatus[im.status] || 0) + 1; });
document.getElementById("resumo").textContent = [`${DADOS.imagens.length} imagem(ns)`,
  ...Object.entries(porStatus).map(([s, n]) => `${n} ${s}${n > 1 ? "s" : ""}`)].join(", ");

function montarLista() {
  lista.replaceChildren();
  DADOS.imagens.forEach((im, i) => {
    const { caixas } = camada(im);
    const li = document.createElement("li");
    const nome = document.createElement("span");
    nome.className = "nome";
    nome.textContent = im.nome;
    const qtd = document.createElement("span");
    qtd.className = "qtd" + (caixas === null || im.invalidas ? " aviso" : "");
    qtd.textContent = caixas === null ? "—" : caixas.length;
    if (im.status) {
      const st = document.createElement("span");
      st.className = `status st-${im.status}`;
      st.textContent = im.status;
      qtd.append(st);
    }
    li.append(nome, qtd);
    li.onclick = () => mostrar(i);
    lista.append(li);
  });
}

function mostrar(i) {
  if (!DADOS.imagens.length) return;
  atual = (i + DADOS.imagens.length) % DADOS.imagens.length;
  const im = DADOS.imagens[atual];
  [...lista.children].forEach((li, j) => li.classList.toggle("atual", j === atual));
  lista.children[atual].scrollIntoView({ block: "nearest" });
  document.getElementById("titulo").textContent =
    `${atual + 1}/${DADOS.imagens.length} · ${im.nome}` + (im.status ? ` · ${im.status}` : "");
  imagem.src = im.src;
  history.replaceState(null, "", `#${atual + 1}`);

  const { tipo, caixas } = camada(im);
  quadro.querySelectorAll(".caixa").forEach(c => c.remove());
  for (const { id, nome, conf, caixa: [x1, y1, x2, y2] } of caixas ?? []) {
    const div = document.createElement("div");
    div.className = "caixa" + (conf === null ? "" : " proposta");
    Object.assign(div.style, {
      left: `${x1 * 100}%`, top: `${y1 * 100}%`,
      width: `${(x2 - x1) * 100}%`, height: `${(y2 - y1) * 100}%`, borderColor: cor(id ?? 0),
    });
    const span = document.createElement("span");
    const rotulo = nome ?? "sem classe";
    span.textContent = conf === null ? rotulo : `${rotulo} ${conf.toFixed(2)}`;
    span.style.background = cor(id ?? 0);
    div.append(span);
    quadro.append(div);
  }
  atualizarVisibilidade();

  const legenda = document.getElementById("legenda");
  legenda.replaceChildren(tipo === "final" ? "Anotação final. " : `Propostas de ${tipo}. `);
  const contagem = {};
  (caixas ?? []).forEach(({ id, nome }) => {
    const chave = JSON.stringify([id, nome]);
    contagem[chave] = (contagem[chave] || 0) + 1;
  });
  for (const [chave, n] of Object.entries(contagem)) {
    const [id, nome] = JSON.parse(chave);
    const item = document.createElement("span");
    const amostra = document.createElement("i");
    amostra.style.background = cor(id ?? 0);
    item.append(amostra, nome === null ? `sem classe: ${n}`
      : `${nome}${id === null ? " (fora do data.yaml)" : ""}: ${n}`);
    legenda.append(item);
  }
  if (caixas === null) legenda.append(tipo === "final"
    ? "Sem arquivo de rótulos em labels/ (não revisada)." : "Sem proposta deste anotador.");
  else if (!caixas.length) legenda.append("Nenhum objeto.");
  if (tipo === "final" && im.invalidas)
    legenda.append(` ${im.invalidas} linha(s) inválida(s) ignorada(s).`);
}

function atualizarVisibilidade() {
  const caixas = document.getElementById("mostrar-caixas").checked;
  quadro.querySelectorAll(".caixa").forEach(c => c.style.display = caixas ? "" : "none");
  quadro.classList.toggle("sem-rotulos", !document.getElementById("mostrar-rotulos").checked);
}

seletor.onchange = () => { montarLista(); mostrar(atual); };
document.getElementById("mostrar-caixas").onchange = atualizarVisibilidade;
document.getElementById("mostrar-rotulos").onchange = atualizarVisibilidade;
document.getElementById("anterior").onclick = () => mostrar(atual - 1);
document.getElementById("proxima").onclick = () => mostrar(atual + 1);
document.addEventListener("keydown", e => {
  if (e.key === "ArrowLeft") mostrar(atual - 1);
  if (e.key === "ArrowRight") mostrar(atual + 1);
});

// #N no endereço abre a N-ésima imagem (e mantém a posição ao recarregar)
montarLista();
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
