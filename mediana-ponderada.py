import networkx as nx

grafo=nx.Graph()

grafo.add_edges_from([
    ("A", "B"),
    ("A", "D"),
    ("B", "C"),
    ("B", "E"),
    ("C", "F"),
    ("D", "E"),
    ("E", "F")
])




pesos = {
    "A": 2,
    "B": 8,
    "C": 3,
    "D": 7,
    "E": 10,
    "F": 5
}

for v in sorted(grafo.nodes):
    grafo.nodes[v]["peso"] = pesos[v]

distancias=dict()



for i in sorted(grafo.nodes):
    distancias[i] = nx.single_source_shortest_path_length(grafo, i)
    #for j in grafo.nodes:
    #    if i in distancias.keys():
    #        distancias[i][j]=(nx.single_source_shortest_path_length(grafo, i)[j])
    #    else:
    #        distancias.setdefault(i, d)
     #       distancias[i][j]=nx.single_source_shortest_path_length(grafo, i)[j]
            



v=0

def C(v):
    lista=list()
    for u in sorted(grafo.nodes):
        lista.append(grafo.nodes[u]["peso"]*distancias[v][u])
    return sum(lista)

min(C(v))

for m in sorted(grafo.nodes):
    print(C(m))
    

