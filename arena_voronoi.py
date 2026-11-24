"""
Arena local para testar estratégias do Jogo de Voronoi em Grafos.

Requisitos:
    - Python 3
    - NetworkX (a mesma biblioteca permitida no projeto)
    - Tkinter (normalmente já vem com Python)

Execute:
    python arena_voronoi.py

A arena é um simulador de testes, não uma implementação de estratégia.
Ela carrega arquivos .py que contenham def estrategia(grafo): ...
"""

import copy
import importlib.util
import math
import random
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

import networkx as nx


# ---------------------------------------------------------------------
# Grafos de exemplo
# ---------------------------------------------------------------------

def add_weights(g, values):
    for v in g.nodes:
        g.nodes[v]["peso"] = values.get(v, 1)
        g.nodes[v]["time"] = 0
    return g


def example_graphs():
    graphs = {}

    g = nx.path_graph(list("ABCDEFGH"))
    graphs["Caminho (8 vértices)"] = add_weights(
        g, dict(zip("ABCDEFGH", [3, 8, 2, 5, 9, 4, 7, 2]))
    )

    g = nx.cycle_graph(list("ABCDEFGH"))
    graphs["Ciclo (8 vértices)"] = add_weights(
        g, dict(zip("ABCDEFGH", [3, 8, 2, 5, 9, 4, 7, 2]))
    )

    g = nx.star_graph(7)
    mapping = {0: "A"}
    mapping.update({i: chr(65 + i) for i in range(1, 8)})
    g = nx.relabel_nodes(g, mapping)
    graphs["Estrela (8 vértices)"] = add_weights(
        g, {"A": 4, "B": 8, "C": 2, "D": 5, "E": 9, "F": 4, "G": 7, "H": 2}
    )

    g = nx.grid_2d_graph(3, 3)
    mapping = {node: chr(65 + i) for i, node in enumerate(sorted(g.nodes()))}
    g = nx.relabel_nodes(g, mapping)
    graphs["Grade 3×3 (9 vértices)"] = add_weights(
        g, dict(zip(g.nodes, [3, 8, 2, 5, 9, 4, 7, 2, 6]))
    )

    g = nx.Graph()
    g.add_edges_from([
        ("A", "B"), ("A", "D"), ("B", "C"), ("B", "E"), ("C", "F"),
        ("D", "E"), ("D", "G"), ("E", "F"), ("E", "H"), ("F", "I"),
        ("G", "H"), ("G", "J"), ("H", "I"), ("H", "K"), ("I", "L"),
        ("J", "K"), ("K", "L"), ("L", "M"), ("K", "M")
    ])
    graphs["Exemplo do professor (13 vértices)"] = add_weights(
        g, {"A": 2, "B": 5, "C": 3, "D": 4, "E": 1, "F": 2,
            "G": 6, "H": 8, "I": 3, "J": 5, "K": 7, "L": 4, "M": 2}
    )

    return graphs


# ---------------------------------------------------------------------
# Estratégias de referência e carregamento de arquivos dos alunos
# ---------------------------------------------------------------------

def random_strategy(g):
    free = [v for v in g.nodes if g.nodes[v]["time"] == 0]
    return random.choice(free)


def max_weight_strategy(g):
    free = [v for v in g.nodes if g.nodes[v]["time"] == 0]
    return max(free, key=lambda v: g.nodes[v]["peso"])


def load_strategy(path):
    path = Path(path)
    spec = importlib.util.spec_from_file_location(
        "strategy_" + path.stem.replace("-", "_"), path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Não foi possível carregar {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    fn = getattr(module, "estrategia", None)
    if not callable(fn):
        raise ValueError(f"{path.name} precisa definir estrategia(grafo).")
    return fn


# ---------------------------------------------------------------------
# Regras do jogo
# ---------------------------------------------------------------------

def distances_from_centers(g, centers):
    if not centers:
        return {}
    result = {}
    for c in centers:
        d = nx.single_source_shortest_path_length(g, c)
        for v, value in d.items():
            if v not in result or value < result[v]:
                result[v] = value
    return result


def territory(g, red_centers, black_centers):
    # Antes de ambas as equipes terem ao menos um centro, ainda não existe
    # comparação territorial útil; mantenha o tabuleiro neutro.
    if not red_centers or not black_centers:
        return {v: "none" for v in g.nodes}, 0.0, 0.0, []

    dr = distances_from_centers(g, red_centers)
    db = distances_from_centers(g, black_centers)
    owners = {}
    red_score = 0.0
    black_score = 0.0
    ties = []

    for v in g.nodes:
        r = dr.get(v, math.inf)
        b = db.get(v, math.inf)
        if r < b:
            owners[v] = "red"
            red_score += g.nodes[v]["peso"]
        elif b < r:
            owners[v] = "black"
            black_score += g.nodes[v]["peso"]
        elif math.isinf(r) and math.isinf(b):
            owners[v] = "none"
        else:
            owners[v] = "tie"
            red_score += g.nodes[v]["peso"] / 2
            black_score += g.nodes[v]["peso"] / 2
            ties.append(v)

    return owners, red_score, black_score, ties


def perspective_copy(g, own_team):
    view = copy.deepcopy(g)
    for v in view.nodes:
        t = view.nodes[v]["time"]
        if own_team == "black":
            if t == 1:
                view.nodes[v]["time"] = 2
            elif t == 2:
                view.nodes[v]["time"] = 1
        # Na visão da estratégia: 1 = próprio; 2 = adversário.
        elif t == 2:
            view.nodes[v]["time"] = 2
    return view


# ---------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------

class VoronoiArena:
    BG = "#f7f7f8"
    RED = "#df1830"
    BLACK = "#242124"
    GREY = "#b9b5b7"
    TEXT = "#292629"

    def __init__(self, root):
        self.root = root
        self.root.title("Arena de Voronoi em Grafos")
        self.root.geometry("1260x820")
        self.root.minsize(1000, 680)

        self.graphs = example_graphs()
        self.graph_name = tk.StringVar(value=list(self.graphs)[0])
        self.starter = tk.StringVar(value="Vermelha")
        self.red_choice = tk.StringVar(value="Aleatória")
        self.black_choice = tk.StringVar(value="Maior peso")
        self.speed = tk.StringVar(value="Normal")
        self.red_file = None
        self.black_file = None

        self.g = None
        self.red_centers = []
        self.black_centers = []
        self.moves = []
        self.round_index = 0
        self.owners = {}
        self.finished = False
        self.after_id = None
        self.positions = {}

        self._build_ui()
        self.reset_game()

    def _build_ui(self):
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill="both", expand=True)

        controls = ttk.Frame(outer)
        controls.pack(fill="x", pady=(0, 10))

        ttk.Label(controls, text="Grafo:").pack(side="left")
        graph_box = ttk.Combobox(
            controls, textvariable=self.graph_name,
            values=list(self.graphs), state="readonly", width=30
        )
        graph_box.pack(side="left", padx=(5, 14))
        graph_box.bind("<<ComboboxSelected>>", lambda _e: self.reset_game())

        ttk.Label(controls, text="Quem começa:").pack(side="left")
        starter_box = ttk.Combobox(
            controls, textvariable=self.starter,
            values=["Vermelha", "Preta"], state="readonly", width=11
        )
        starter_box.pack(side="left", padx=5)
        starter_box.bind("<<ComboboxSelected>>", lambda _e: self.reset_game())

        ttk.Label(controls, text="Velocidade:").pack(side="left", padx=(12, 3))
        speed_box = ttk.Combobox(
            controls, textvariable=self.speed,
            values=["Lenta", "Normal", "Rápida"], state="readonly", width=9
        )
        speed_box.pack(side="left")

        ttk.Button(controls, text="Reiniciar", command=self.reset_game).pack(
            side="right", padx=(6, 0)
        )
        self.play_button = ttk.Button(
            controls, text="▶ Jogar partida", command=self.play_match
        )
        self.play_button.pack(side="right", padx=6)
        self.next_button = ttk.Button(
            controls, text="Próximo lance", command=self.next_move
        )
        self.next_button.pack(side="right", padx=6)

        strategy_frame = ttk.LabelFrame(outer, text="Estratégias", padding=8)
        strategy_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(strategy_frame, text="Equipe vermelha:").grid(
            row=0, column=0, sticky="w"
        )
        self.red_box = ttk.Combobox(
            strategy_frame, textvariable=self.red_choice,
            values=["Aleatória", "Maior peso", "Arquivo Python..."],
            state="readonly", width=22
        )
        self.red_box.grid(row=0, column=1, padx=5, sticky="w")
        self.red_box.bind("<<ComboboxSelected>>", lambda _e: self.choose_file("red"))

        ttk.Label(strategy_frame, text="Equipe preta:").grid(
            row=0, column=2, sticky="w", padx=(20, 0)
        )
        self.black_box = ttk.Combobox(
            strategy_frame, textvariable=self.black_choice,
            values=["Aleatória", "Maior peso", "Arquivo Python..."],
            state="readonly", width=22
        )
        self.black_box.grid(row=0, column=3, padx=5, sticky="w")
        self.black_box.bind("<<ComboboxSelected>>", lambda _e: self.choose_file("black"))

        self.red_file_label = ttk.Label(strategy_frame, text="Nenhum arquivo selecionado")
        self.red_file_label.grid(row=1, column=1, sticky="w", padx=5)
        self.black_file_label = ttk.Label(strategy_frame, text="Nenhum arquivo selecionado")
        self.black_file_label.grid(row=1, column=3, sticky="w", padx=5)

        main = ttk.Frame(outer)
        main.pack(fill="both", expand=True)

        left = ttk.Frame(main)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        score_frame = ttk.Frame(left)
        score_frame.pack(fill="x", pady=(0, 8))
        self.red_score_label = ttk.Label(
            score_frame, text="VERMELHA  0,0",
            background=self.RED, foreground="white",
            font=("TkDefaultFont", 14, "bold"), padding=12
        )
        self.red_score_label.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.black_score_label = ttk.Label(
            score_frame, text="PRETA  0,0",
            background=self.BLACK, foreground="white",
            font=("TkDefaultFont", 14, "bold"), padding=12
        )
        self.black_score_label.pack(side="left", fill="x", expand=True, padx=(4, 0))

        self.status = ttk.Label(left, text="", font=("TkDefaultFont", 11, "bold"))
        self.status.pack(fill="x", pady=(0, 5))

        self.canvas = tk.Canvas(
            left, background="white", highlightthickness=1,
            highlightbackground="#dedadd", height=510
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _e: self.draw_graph())

        self.explanation = ttk.Label(
            left, text="Escolha as estratégias e inicie a partida.",
            wraplength=780, justify="left", padding=9,
            background="#efedef"
        )
        self.explanation.pack(fill="x", pady=(8, 0))

        right = ttk.Frame(main, width=330)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        ttk.Label(right, text="HISTÓRICO DE LANCES",
                  font=("TkDefaultFont", 11, "bold")).pack(anchor="w")
        self.history = tk.Listbox(right, height=15, font=("TkDefaultFont", 10))
        self.history.pack(fill="x", pady=(5, 10))
        self.history.bind("<<ListboxSelect>>", self.show_selected_move)

        ttk.Label(right, text="RELATÓRIO",
                  font=("TkDefaultFont", 11, "bold")).pack(anchor="w")
        self.report = tk.Text(right, height=18, wrap="word", font=("TkDefaultFont", 10))
        self.report.pack(fill="both", expand=True, pady=(5, 0))
        self.report.insert("1.0", "O relatório final aparecerá aqui.")
        self.report.configure(state="disabled")

        legend = ttk.Label(
            outer,
            text="Legenda: círculo vermelho/preto = território; anel duplo = centro escolhido; "
                 "número pequeno = peso do vértice; cinza = empate ou sem dono.",
            wraplength=1150
        )
        legend.pack(fill="x", pady=(8, 0))

    def choose_file(self, team):
        path = filedialog.askopenfilename(
            title="Selecione um arquivo Python com estrategia(grafo)",
            filetypes=[("Arquivos Python", "*.py"), ("Todos os arquivos", "*.*")]
        )
        if not path:
            if team == "red":
                self.red_choice.set("Aleatória")
            else:
                self.black_choice.set("Maior peso")
            return
        if team == "red":
            self.red_file = path
            self.red_choice.set("Arquivo Python...")
            self.red_file_label.config(text=Path(path).name)
        else:
            self.black_file = path
            self.black_choice.set("Arquivo Python...")
            self.black_file_label.config(text=Path(path).name)

    def get_strategy(self, team):
        choice = self.red_choice.get() if team == "red" else self.black_choice.get()
        path = self.red_file if team == "red" else self.black_file
        if choice == "Aleatória":
            return random_strategy
        if choice == "Maior peso":
            return max_weight_strategy
        if not path:
            raise ValueError(f"Selecione o arquivo Python da equipe {team}.")
        return load_strategy(path)

    def reset_game(self):
        self.stop_auto()
        self.positions = {}
        self.g = copy.deepcopy(self.graphs[self.graph_name.get()])
        self.red_centers = []
        self.black_centers = []
        self.moves = []
        self.round_index = 0
        self.finished = False
        self.owners = {v: "none" for v in self.g.nodes}
        self.history.delete(0, "end")
        self._set_report("A partida ainda não terminou.")
        self.explanation.config(text="Partida reiniciada. Escolha as estratégias e avance lance a lance.")
        self.update_view()

    def team_for_round(self, index):
        first = "red" if self.starter.get() == "Vermelha" else "black"
        second = "black" if first == "red" else "red"
        return first if index % 2 == 0 else second

    def next_move(self):
        if self.finished:
            return
        if self.round_index >= 6:
            self.finish_game()
            return
        team = self.team_for_round(self.round_index)
        try:
            strategy = self.get_strategy(team)
            view = copy.deepcopy(self.g)
            for v in view.nodes:
                current = view.nodes[v]["time"]
                if team == "red":
                    view.nodes[v]["time"] = 1 if current == 1 else (2 if current == 2 else 0)
                else:
                    view.nodes[v]["time"] = 1 if current == 2 else (2 if current == 1 else 0)
            chosen = strategy(view)
            if chosen not in self.g:
                raise ValueError(f"A estratégia retornou vértice inexistente: {chosen!r}")
            if self.g.nodes[chosen]["time"] != 0:
                raise ValueError(f"A estratégia escolheu {chosen!r}, que já está ocupado.")

            self.g.nodes[chosen]["time"] = 1 if team == "red" else 2
            centers = self.red_centers if team == "red" else self.black_centers
            centers.append(chosen)
            self.round_index += 1

            owners, rs, bs, ties = territory(self.g, self.red_centers, self.black_centers)
            self.owners = owners
            team_name = "Vermelha" if team == "red" else "Preta"
            weight = self.g.nodes[chosen]["peso"]
            self.moves.append({
                "round": self.round_index,
                "team": team,
                "team_name": team_name,
                "vertex": chosen,
                "weight": weight,
                "red_score": rs,
                "black_score": bs,
                "ties": list(ties),
                "owners": dict(owners),
            })
            self.history.insert(
                "end", f"Lance {self.round_index}: {team_name} → {chosen} (peso {weight})"
            )
            self.history.selection_clear(0, "end")
            self.history.selection_set("end")
            self.explanation.config(
                text=f"{team_name} escolheu {chosen} (peso {weight}). "
                     f"Placar territorial provisório: vermelha {rs:g} × preta {bs:g}. "
                     f"Empates atuais: {len(ties)} vértice(s)."
            )
            self.update_view()
            if self.round_index == 6:
                self.finish_game()
        except Exception as exc:
            messagebox.showerror(
                "Erro ao executar estratégia",
                f"A partida foi pausada.\n\n{type(exc).__name__}: {exc}"
            )
            self.stop_auto()

    def play_match(self):
        if self.finished:
            self.reset_game()
        self.stop_auto()
        self._auto_step()

    def _auto_step(self):
        if self.finished:
            return
        self.next_move()
        if not self.finished:
            delay = {"Lenta": 2400, "Normal": 1400, "Rápida": 650}.get(
                self.speed.get(), 1400
            )
            self.after_id = self.root.after(delay, self._auto_step)

    def stop_auto(self):
        if self.after_id is not None:
            try:
                self.root.after_cancel(self.after_id)
            except Exception:
                pass
            self.after_id = None

    def finish_game(self):
        self.stop_auto()
        if self.finished:
            return
        self.finished = True
        owners, rs, bs, ties = territory(
            self.g, self.red_centers, self.black_centers
        )
        self.owners = owners
        result = "Vermelha venceu" if rs > bs else ("Preta venceu" if bs > rs else "Empate")
        self.explanation.config(
            text=f"PARTIDA ENCERRADA — {result}. Placar final: "
                 f"vermelha {rs:g} × preta {bs:g}."
        )
        self._make_final_report(rs, bs, ties, result)
        self.update_view()

    def _make_final_report(self, rs, bs, ties, result):
        total = sum(self.g.nodes[v]["peso"] for v in self.g.nodes)
        red_nodes = [v for v in self.g.nodes if self.owners.get(v) == "red"]
        black_nodes = [v for v in self.g.nodes if self.owners.get(v) == "black"]
        tied_nodes = [v for v in self.g.nodes if self.owners.get(v) == "tie"]
        lines = [
            f"RESULTADO: {result}",
            f"Placar: Vermelha {rs:g} × Preta {bs:g}",
            f"Diferença: {abs(rs-bs):g} ponto(s)",
            f"Peso total do grafo: {total}",
            "",
            "CENTROS ESCOLHIDOS",
            f"Vermelha: {', '.join(map(str, self.red_centers)) or 'nenhum'}",
            f"Preta: {', '.join(map(str, self.black_centers)) or 'nenhum'}",
            "",
            "DISTRIBUIÇÃO TERRITORIAL",
            f"Vermelha: {len(red_nodes)} vértice(s) exclusivos — {', '.join(map(str, red_nodes)) or 'nenhum'}",
            f"Preta: {len(black_nodes)} vértice(s) exclusivos — {', '.join(map(str, black_nodes)) or 'nenhum'}",
            f"Empate: {len(tied_nodes)} vértice(s) — {', '.join(map(str, tied_nodes)) or 'nenhum'}",
            "",
            "PONTUAÇÃO POR LANCE (provisória após cada escolha)",
        ]
        for m in self.moves:
            lines.append(
                f"{m['round']}. {m['team_name']} escolheu {m['vertex']} "
                f"(peso {m['weight']}) — V {m['red_score']:g} × P {m['black_score']:g}"
            )
        lines += [
            "",
            "LEITURA DO RESULTADO",
            "Os valores territoriais após cada lance são provisórios: escolhas posteriores "
            "podem alterar a propriedade de vértices. O placar final considera os seis centros.",
            "Empates dividem o peso do vértice igualmente entre as equipes."
        ]
        self._set_report("\n".join(lines))

    def _set_report(self, text):
        self.report.configure(state="normal")
        self.report.delete("1.0", "end")
        self.report.insert("1.0", text)
        self.report.configure(state="disabled")

    def show_selected_move(self, _event=None):
        selection = self.history.curselection()
        if not selection:
            return
        idx = selection[0]
        if idx >= len(self.moves):
            return
        m = self.moves[idx]
        self.owners = dict(m["owners"])
        self.explanation.config(
            text=f"Visualização após o lance {m['round']}: {m['team_name']} escolheu "
                 f"{m['vertex']} (peso {m['weight']}). Placar provisório: "
                 f"vermelha {m['red_score']:g} × preta {m['black_score']:g}. "
                 f"Empates: {', '.join(map(str, m['ties'])) or 'nenhum'}."
        )
        self.draw_graph()

    def update_view(self):
        if self.round_index == 0:
            self.status.config(
                text=f"Partida 1 • começa {self.starter.get()} • aguardando primeiro lance"
            )
            self.red_score_label.config(text="VERMELHA  —")
            self.black_score_label.config(text="PRETA  —")
        else:
            next_team = self.team_for_round(min(self.round_index, 5))
            next_name = "Vermelha" if next_team == "red" else "Preta"
            if self.finished:
                next_name = "Partida encerrada"
            self.status.config(
                text=f"Lance {self.round_index} de 6 • "
                     f"{'vez de ' + next_name if not self.finished else next_name}"
            )
            _, rs, bs, _ = territory(self.g, self.red_centers, self.black_centers)
            self.red_score_label.config(text=f"VERMELHA  {rs:g}")
            self.black_score_label.config(text=f"PRETA  {bs:g}")
        self.draw_graph()

    def draw_graph(self):
        if self.g is None:
            return
        self.canvas.delete("all")
        width = max(self.canvas.winfo_width(), 400)
        height = max(self.canvas.winfo_height(), 350)
        margin = 55

        if not self.positions:
            self._calculate_positions()
        xs = [p[0] for p in self.positions.values()]
        ys = [p[1] for p in self.positions.values()]
        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)
        rangex = max(maxx - minx, 0.01)
        rangey = max(maxy - miny, 0.01)
        scale = min((width - 2*margin)/rangex, (height - 2*margin)/rangey)
        offsetx = (width - scale*rangex)/2
        offsety = (height - scale*rangey)/2

        screen = {}
        for v, (x, y) in self.positions.items():
            sx = offsetx + (x-minx)*scale
            sy = offsety + (y-miny)*scale
            screen[v] = (sx, sy)

        for u, v in self.g.edges:
            x1, y1 = screen[u]
            x2, y2 = screen[v]
            self.canvas.create_line(x1, y1, x2, y2, fill="#c7c2c5", width=3)

        centers = set(self.red_centers + self.black_centers)
        for v, (x, y) in screen.items():
            owner = self.owners.get(v, "none")
            if owner == "red":
                fill = self.RED
            elif owner == "black":
                fill = self.BLACK
            else:
                fill = "#a9a5a8"

            r = 24
            if v in centers:
                ring = self.RED if v in self.red_centers else self.BLACK
                self.canvas.create_oval(
                    x-r-6, y-r-6, x+r+6, y+r+6,
                    outline=ring, width=3
                )
            self.canvas.create_oval(
                x-r, y-r, x+r, y+r, fill=fill,
                outline="white", width=2
            )
            self.canvas.create_text(
                x, y, text=str(v), fill="white",
                font=("TkDefaultFont", 12, "bold")
            )
            self.canvas.create_oval(
                x+14, y-29, x+37, y-6,
                fill="white", outline="#d7d2d5", width=1
            )
            self.canvas.create_text(
                x+25.5, y-17.5,
                text=str(self.g.nodes[v]["peso"]),
                fill=self.TEXT, font=("TkDefaultFont", 9, "bold")
            )

    def _calculate_positions(self):
        # Layout determinístico para grafos de exemplo; spring_layout funciona
        # também para grafos personalizados que venham a ser adicionados depois.
        if self.graph_name.get().startswith("Caminho"):
            self.positions = {v: (i, 0) for i, v in enumerate(self.g.nodes)}
        elif self.graph_name.get().startswith("Ciclo"):
            n = len(self.g)
            self.positions = {
                v: (math.cos(2*math.pi*i/n), math.sin(2*math.pi*i/n))
                for i, v in enumerate(self.g.nodes)
            }
        elif self.graph_name.get().startswith("Estrela"):
            center = "A"
            self.positions = {center: (0, 0)}
            leaves = [v for v in self.g.nodes if v != center]
            for i, v in enumerate(leaves):
                angle = 2*math.pi*i/len(leaves)
                self.positions[v] = (math.cos(angle), math.sin(angle))
        elif self.graph_name.get().startswith("Grade"):
            coords = {
                "A": (0, 0), "B": (1, 0), "C": (2, 0),
                "D": (0, 1), "E": (1, 1), "F": (2, 1),
                "G": (0, 2), "H": (1, 2), "I": (2, 2)
            }
            self.positions = coords
        else:
            self.positions = nx.spring_layout(self.g, seed=17)


if __name__ == "__main__":
    root = tk.Tk()
    app = VoronoiArena(root)
    root.mainloop()
