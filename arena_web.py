#!/usr/bin/env python3
"""
Arena Web - Jogo de Voronoi em Grafos (app local).

Uso:   python arena_web.py          (abre http://127.0.0.1:8765)
Teste: python arena_web.py --test

Requer apenas Python 3 e networkx. Envie estratégias (.py com
def estrategia(grafo)) e grafos (JSON) pelo navegador. O confronto segue a
engine do professor: duas partidas (A começa, B começa) e placares somados.
A = Equipe 1 (vermelha), B = Equipe 2 (azul).
ATENÇÃO: os arquivos .py enviados são EXECUTADOS nesta máquina (servidor
só escuta em 127.0.0.1).
"""
import copy
import json
import math
import random
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

import networkx as nx

INF = math.inf
RODADAS = 6

# ----------------------------- grafos de exemplo -----------------------------
def _spec(g, pesos, pos):
    return {"nodes": {str(v): pesos[i] for i, v in enumerate(g.nodes)},
            "edges": [[str(a), str(b)] for a, b in g.edges],
            "pos": {str(v): [float(p[0]), float(p[1])] for v, p in pos.items()}}


def examples():
    L = list("ABCDEFGH")
    w8 = [3, 8, 2, 5, 9, 4, 7, 2]
    out = {}
    g = nx.path_graph(L)
    out["Caminho (8)"] = _spec(g, w8, {v: (i, 0) for i, v in enumerate(L)})
    g = nx.cycle_graph(L)
    out["Ciclo (8)"] = _spec(g, w8, nx.circular_layout(g))
    g = nx.Graph([("A", c) for c in L[1:]])
    pos = nx.circular_layout(g.subgraph(L[1:]))
    pos["A"] = (0, 0)
    out["Estrela (8)"] = _spec(g, [4, 8, 2, 5, 9, 4, 7, 2], pos)
    g = nx.Graph()
    pos = {}
    for r in range(3):
        for c in range(3):
            v = chr(65 + 3 * r + c)
            g.add_node(v)
            pos[v] = (c, r)
            if c: g.add_edge(chr(64 + 3 * r + c), v)
            if r: g.add_edge(chr(62 + 3 * r + c), v)
    out["Grade 3x3 (9)"] = _spec(g, [3, 8, 2, 5, 9, 4, 7, 2, 6], pos)
    g = nx.Graph([("A", "B"), ("A", "D"), ("B", "C"), ("B", "E"), ("C", "F"),
                  ("D", "E"), ("D", "G"), ("E", "F"), ("E", "H"), ("F", "I"),
                  ("G", "H"), ("G", "J"), ("H", "I"), ("H", "K"), ("I", "L"),
                  ("J", "K"), ("K", "L"), ("L", "M"), ("K", "M")])
    p = {"A": 2, "B": 5, "C": 3, "D": 4, "E": 1, "F": 2, "G": 6, "H": 8,
         "I": 3, "J": 5, "K": 7, "L": 4, "M": 2}
    out["Exemplo do professor (13)"] = _spec(
        g, [p[v] for v in g.nodes], nx.spring_layout(g, seed=17))
    return out


# ------------------------------ regras do jogo -------------------------------
def build_graph(spec):
    if not isinstance(spec, dict) or not isinstance(spec.get("nodes"), dict):
        raise ValueError('Grafo inválido: use {"nodes": {id: peso}, "edges": [[u, v]]}.')
    g = nx.Graph()
    for v, w in spec["nodes"].items():
        if isinstance(w, bool) or not isinstance(w, (int, float)):
            raise ValueError(f"Peso inválido no vértice {v!r}.")
        g.add_node(str(v), peso=w, time=0)
    for e in spec.get("edges", []):
        u, v = str(e[0]), str(e[1])
        if u not in g or v not in g:
            raise ValueError(f"Aresta {u}-{v} usa vértice inexistente.")
        g.add_edge(u, v)
    if len(g) < RODADAS:
        raise ValueError(f"O grafo precisa de ao menos {RODADAS} vértices.")
    return g


def _dists(g, centers):
    d = {}
    for c in centers:
        for v, k in nx.single_source_shortest_path_length(g, c).items():
            if k < d.get(v, INF):
                d[v] = k
    return d


def territory(g, red, black):
    """owners, placar vermelho, placar azul. Sem alcance -> 'none'.
    Com centros de um time só, ele domina tudo que alcança."""
    if not red and not black:
        return {v: "none" for v in g}, 0.0, 0.0
    dr, db = _dists(g, red), _dists(g, black)
    owners, rs, bs = {}, 0.0, 0.0
    for v in g:
        r, b, w = dr.get(v, INF), db.get(v, INF), g.nodes[v]["peso"]
        if r < b:
            owners[v] = "red"; rs += w
        elif b < r:
            owners[v] = "black"; bs += w
        elif r == INF:
            owners[v] = "none"
        else:
            owners[v] = "tie"; rs += w / 2; bs += w / 2
    return owners, rs, bs


def load_strategy(spec, label):
    kind = spec.get("kind")
    if kind == "random":
        return lambda g: random.choice([v for v in g if g.nodes[v]["time"] == 0])
    if kind == "maxw":
        return lambda g: max((v for v in g if g.nodes[v]["time"] == 0),
                             key=lambda v: g.nodes[v]["peso"])
    if kind == "code" and spec.get("code"):
        ns = {"__name__": f"estrategia_{label}"}
        try:
            exec(compile(spec["code"], spec.get("name", label), "exec"), ns)
        except Exception as e:
            raise ValueError(f"Erro ao carregar a estratégia {label}: {type(e).__name__}: {e}")
        if not callable(ns.get("estrategia")):
            raise ValueError(f"A estratégia {label} precisa definir estrategia(grafo).")
        return ns["estrategia"]
    raise ValueError(f"Escolha ou envie um arquivo para a estratégia {label}.")


def play(base, fa, fb, first):
    g = copy.deepcopy(base)
    red, black, moves, error = [], [], [], None
    for i in range(RODADAS):
        team = first if i % 2 == 0 else ("B" if first == "A" else "A")
        view = copy.deepcopy(g)
        if team == "B":  # perspectiva normalizada: 1 = meu, 2 = adversário
            for v in view:
                t = view.nodes[v]["time"]
                view.nodes[v]["time"] = {1: 2, 2: 1}.get(t, 0)
        try:
            v = (fa if team == "A" else fb)(view)
            if v not in g:
                raise ValueError(f"retornou {v!r}, que não existe no grafo")
            if g.nodes[v]["time"] != 0:
                raise ValueError(f"escolheu {v!r}, que já está ocupado")
        except Exception as e:
            error = f"Estratégia {team} (lance {i + 1}): {type(e).__name__}: {e}"
            break
        g.nodes[v]["time"] = 1 if team == "A" else 2
        (red if team == "A" else black).append(v)
        owners, rs, bs = territory(g, red, black)
        moves.append({"team": team, "vertex": v, "peso": g.nodes[v]["peso"],
                      "owners": owners, "red": list(red), "black": list(black),
                      "rs": rs, "bs": bs})
    return {"first": first, "moves": moves, "error": error}


def simulate(body):
    g = build_graph(body["graph"])
    fa, fb = load_strategy(body["A"], "A"), load_strategy(body["B"], "B")
    partidas = [play(g, fa, fb, "A"), play(g, fa, fb, "B")]
    ok = all(p["error"] is None for p in partidas)
    tot = [sum(p["moves"][-1][k] for p in partidas) for k in ("rs", "bs")] if ok else None
    pos = body["graph"].get("pos") or nx.spring_layout(g, seed=17)
    pos = {str(k): [float(x), float(y)] for k, (x, y) in pos.items()}
    return {"nodes": [{"id": v, "peso": g.nodes[v]["peso"]} for v in g],
            "edges": [list(e) for e in g.edges], "pos": pos, "partidas": partidas,
            "total": tot, "connected": nx.is_connected(g)}


# ----------------------------- servidor e interface ---------------------------
HTML = r"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Arena Web de Voronoi</title><style>
:root{--bg:#eef1f5;--panel:#fff;--ink:#1b2430;--mut:#5d6b7c;--line:#d5dce5;--red:#d6283b;--blu:#3b7bf0;--acc:#0f7b6c;--onacc:#fff;}
@media(prefers-color-scheme:dark){:root{--bg:#14181e;--panel:#1d232b;--ink:#e8edf3;--mut:#9aa8b8;--line:#323c48;--acc:#3fc1ad;--onacc:#0b1f1c}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,"Segoe UI",sans-serif;display:grid;grid-template-columns:340px 1fr;gap:16px;padding:16px;min-height:100vh}
@media(max-width:900px){body{grid-template-columns:1fr}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:14px;margin-bottom:14px}
h1{font-size:19px;margin:0 0 12px}h2{font-size:14px;margin:0 0 8px}
select,textarea,button,input{font:inherit;color:inherit;width:100%;margin:3px 0 8px}
select,textarea,input{background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:6px}
textarea{height:130px;font:12px monospace}
button{background:var(--acc);color:var(--onacc);border:0;border-radius:6px;padding:9px;cursor:pointer;font-weight:600}
button.sec{background:none;color:var(--ink);border:1px solid var(--line);width:auto;padding:5px 12px;margin:0 4px 0 0}
button.sec.on{border-color:var(--acc);color:var(--acc)}
:focus-visible{outline:2px solid var(--acc);outline-offset:2px}
.sc{display:flex;gap:10px}.sc div{flex:1;color:#fff;padding:10px;border-radius:6px;font-weight:700;font-size:17px}
#sa{background:var(--red)}#sb{background:var(--blu)}
.msg{color:var(--red);font-weight:600;margin:6px 0}.warn{color:#a35b00;margin:6px 0}
svg{width:100%;height:auto;background:var(--panel);border:1px solid var(--line);border-radius:8px}
#mv button{display:block;width:100%;text-align:left;background:none;color:var(--ink);font-weight:400;border-bottom:1px solid var(--line);border-radius:0;margin:0;padding:5px}
#mv button.cur{background:var(--bg);font-weight:700}
pre{white-space:pre-wrap;font:13px/1.5 system-ui;margin:0}.k{color:var(--mut);font-size:13px}
</style></head><body>
<aside>
<div class="card"><h1>Arena Web de Voronoi</h1>
<h2>Grafo</h2>
<select id="gsel" aria-label="Grafo de exemplo"></select>
<textarea id="gjson" spellcheck="false" aria-label="JSON do grafo"></textarea>
<input type="file" id="gfile" accept=".json" aria-label="Enviar grafo JSON">
<div class="k">Formato: {"nodes":{"A":3,...},"edges":[["A","B"],...]} (pos opcional). Ids viram texto.</div></div>
<div class="card"><h2>Estratégia A (vermelha, Equipe 1)</h2>
<select id="sA"><option value="random">Aleatória</option><option value="maxw">Maior peso</option><option value="code">Arquivo .py</option></select>
<input type="file" id="fA" accept=".py" aria-label="Arquivo da estratégia A">
<h2>Estratégia B (azul, Equipe 2)</h2>
<select id="sB"><option value="random">Aleatória</option><option value="maxw" selected>Maior peso</option><option value="code">Arquivo .py</option></select>
<input type="file" id="fB" accept=".py" aria-label="Arquivo da estratégia B">
<button id="go">Simular confronto (2 partidas)</button><div id="msg" class="msg" role="alert"></div></div>
</aside>
<main><div id="out" hidden>
<div class="card"><div id="tot"></div><div id="warn" class="warn"></div><div id="err" class="msg"></div></div>
<div class="card"><div id="tabs"></div>
<div class="sc" style="margin:10px 0"><div id="sa"></div><div id="sb"></div></div>
<svg id="svg" viewBox="0 0 720 460" role="img" aria-label="Grafo"><defs>
<linearGradient id="tie" x1="0" y1="0" x2="1" y2="1"><stop offset=".5" stop-color="#d6283b"/><stop offset=".5" stop-color="#3b7bf0"/></linearGradient></defs><g id="gg"></g></svg>
<input type="range" id="sl" min="0" max="6" value="6" aria-label="Lance exibido">
<div class="k">Círculo cheio = território; metade vermelha/azul = empate; tracejado cinza = sem dono; anel = centro escolhido até o lance exibido.</div></div>
<div class="card"><h2>Histórico (clique para ver aquele momento)</h2><div id="mv"></div></div>
<div class="card"><h2>Relatório</h2><pre id="rep"></pre></div></div></main>
<script>
const $=s=>document.querySelector(s),NS="http://www.w3.org/2000/svg";
function el(t,a,txt,ns){const e=ns?document.createElementNS(NS,t):document.createElement(t);for(const k in a||{})e.setAttribute(k,a[k]);if(txt!=null)e.textContent=txt;return e}
const code={A:null,B:null};let ex={},D=null,pi=0,step=0;
const fmt=x=>Number.isInteger(x)?String(x):x.toFixed(1).replace(".",",");
const msg=t=>$("#msg").textContent=t;
for(const T of["A","B"])$("#f"+T).onchange=async e=>{const f=e.target.files[0];if(f){code[T]={code:await f.text(),name:f.name};$("#s"+T).value="code"}};
$("#gfile").onchange=async e=>{const f=e.target.files[0];if(f)$("#gjson").value=await f.text()};
$("#gsel").onchange=()=>$("#gjson").value=JSON.stringify(ex[$("#gsel").value]);
function spec(T){const k=$("#s"+T).value;if(k!=="code")return{kind:k};if(!code[T])throw new Error("Envie o arquivo .py da estratégia "+T+".");return{kind:"code",...code[T]}}
$("#go").onclick=async()=>{msg("");let body;
 try{body={graph:JSON.parse($("#gjson").value),A:spec("A"),B:spec("B")}}catch(e){return msg(e.message)}
 const j=await(await fetch("/api/simulate",{method:"POST",body:JSON.stringify(body)})).json();
 if(j.error)return msg(j.error);D=j;pi=0;step=D.partidas[0].moves.length;render()};
$("#sl").oninput=e=>{step=+e.target.value;render()};
function render(){const P=D.partidas[pi],M=P.moves;$("#out").hidden=false;
 $("#tot").textContent=D.total?`Confronto: A ${fmt(D.total[0])} × B ${fmt(D.total[1])} — `+(D.total[0]>D.total[1]?"Equipe 1 (A) vence":D.total[1]>D.total[0]?"Equipe 2 (B) vence":"empate"):"Confronto incompleto (erro em uma estratégia).";
 $("#warn").textContent=D.connected?"":"Aviso: grafo desconexo. A arena pontua, mas a engine do professor lançaria KeyError.";
 $("#err").textContent=D.partidas.map((p,i)=>p.error?`Partida ${i+1}: ${p.error}`:"").filter(Boolean).join(" | ");
 const tabs=$("#tabs");tabs.replaceChildren();
 D.partidas.forEach((p,i)=>{const b=el("button",{class:"sec"+(i===pi?" on":"")},`Partida ${i+1} (${p.first} começa)`);b.onclick=()=>{pi=i;step=D.partidas[i].moves.length;render()};tabs.append(b)});
 const sl=$("#sl");sl.max=M.length;step=Math.min(step,M.length);sl.value=step;
 const s=step?M[step-1]:null;
 $("#sa").textContent="A (vermelha)  "+(s?fmt(s.rs):"—");$("#sb").textContent="B (azul)  "+(s?fmt(s.bs):"—");
 draw(s);
 const mv=$("#mv");mv.replaceChildren();
 M.forEach((m,i)=>{const b=el("button",{class:i+1===step?"cur":""},`Lance ${i+1}: ${m.team} → ${m.vertex} (peso ${m.peso}) · Verm ${fmt(m.rs)} × Azul ${fmt(m.bs)}`);b.onclick=()=>{step=i+1;render()};mv.append(b)});
 const f=M[M.length-1],L=[];
 D.partidas.forEach((p,i)=>{const l=p.moves[p.moves.length-1];if(l)L.push(`Partida ${i+1} (${p.first} começa): A ${fmt(l.rs)} × B ${fmt(l.bs)}\n  centros A: ${l.red.join(", ")} | centros B: ${l.black.join(", ")}\n  empates: ${D.nodes.filter(n=>l.owners[n.id]==="tie").map(n=>n.id).join(", ")||"nenhum"}`)});
 $("#rep").textContent=L.join("\n\n")+(f?"\n\nValores por lance são provisórios; o placar final usa os 6 centros.":"")}
function draw(s){const g=$("#gg");g.replaceChildren();const ids=D.nodes.map(n=>n.id),P=D.pos;
 const xs=ids.map(v=>P[v][0]),ys=ids.map(v=>P[v][1]),x0=Math.min(...xs),y0=Math.min(...ys);
 const rx=Math.max(Math.max(...xs)-x0,1e-6),ry=Math.max(Math.max(...ys)-y0,1e-6);
 const sc=Math.min(620/rx,360/ry),ox=(720-sc*rx)/2,oy=(460-sc*ry)/2;
 const at=v=>[ox+(P[v][0]-x0)*sc,oy+(P[v][1]-y0)*sc];
 for(const[u,v]of D.edges){const a=at(u),b=at(v);g.append(el("line",{x1:a[0],y1:a[1],x2:b[0],y2:b[1],stroke:"#9aa8b8","stroke-width":3},null,1))}
 for(const n of D.nodes){const[x,y]=at(n.id),o=s?s.owners[n.id]:"none";
  const fill=o==="red"?"#d6283b":o==="black"?"#3b7bf0":o==="tie"?"url(#tie)":"#cfd6df";
  const isR=s&&s.red.includes(n.id),isB=s&&s.black.includes(n.id);
  if(isR||isB)g.append(el("circle",{cx:x,cy:y,r:31,fill:"none",stroke:isR?"#d6283b":"#3b7bf0","stroke-width":4},null,1));
  g.append(el("circle",{cx:x,cy:y,r:24,fill,stroke:o==="none"?"#7d8b9b":"#fff","stroke-width":2,"stroke-dasharray":o==="none"?"4 3":"0"},null,1));
  g.append(el("text",{x,y:y+5,"text-anchor":"middle","font-weight":700,"font-size":15,fill:o==="none"?"#1b2430":"#fff"},n.id,1));
  g.append(el("circle",{cx:x+22,cy:y-24,r:11,fill:"#fff",stroke:"#9aa8b8"},null,1));
  g.append(el("text",{x:x+22,y:y-20,"text-anchor":"middle","font-size":11,"font-weight":700,fill:"#1b2430"},fmt(n.peso),1))}}
(async()=>{ex=await(await fetch("/api/examples")).json();for(const n in ex)$("#gsel").append(el("option",{value:n},n));$("#gsel").onchange()})();
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/":
            self._send(200, HTML, "text/html; charset=utf-8")
        elif self.path == "/api/examples":
            self._send(200, json.dumps(examples()))
        else:
            self._send(404, "{}")

    def do_POST(self):
        if self.path != "/api/simulate":
            return self._send(404, "{}")
        try:
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            self._send(200, json.dumps(simulate(body)))
        except Exception as e:  # erro de entrada vira mensagem na tela
            self._send(200, json.dumps({"error": f"{type(e).__name__}: {e}"}))

    def log_message(self, *a):
        pass


def self_test():
    ex = examples()
    g = build_graph(ex["Caminho (8)"])
    _, rs, bs = territory(g, ["B"], ["G"])
    assert (rs, bs) == (18, 22), (rs, bs)
    d = nx.Graph([("A", "B"), ("C", "D")])
    for v in d: d.nodes[v].update(peso=1, time=0)
    assert territory(d, ["A"], ["C"])[1:] == (2, 2)  # desconexo não quebra
    for name, spec in ex.items():
        r = simulate({"graph": spec, "A": {"kind": "maxw"}, "B": {"kind": "random"}})
        assert all(len(p["moves"]) == 6 and not p["error"] for p in r["partidas"]), name
        assert abs(sum(r["total"]) - 2 * sum(spec["nodes"].values())) < 1e-9, name
    bad = simulate({"graph": ex["Ciclo (8)"], "A": {"kind": "code", "code": "def estrategia(g): return 'ZZ'"}, "B": {"kind": "maxw"}})
    assert bad["partidas"][0]["error"] and bad["total"] is None
    print("autoteste OK")


if __name__ == "__main__":
    if "--test" in sys.argv:
        self_test()
    else:
        srv = HTTPServer(("127.0.0.1", 8765), Handler)
        print("Arena Web em http://127.0.0.1:8765  (Ctrl+C para sair)")
        threading.Timer(0.8, lambda: webbrowser.open("http://127.0.0.1:8765")).start()
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass
