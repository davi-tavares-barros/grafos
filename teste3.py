import networkx as nx

def estrategia_md(grafo):
    pesos={}
    distancias={}
    pesos.keys=grafo.nodes
    time_de_cada_vertice=[]
    segundo_turno_é_nosso=False
    gargalos = list(nx.articulation_points(grafo))
    pontes = list(nx.bridges(grafo))
    centralidade = nx.betweenness_centrality(grafo)

    for u in grafo.nodes:
        if grafo.nodes[u]["time"]==1:
            time_de_cada_vertice.append(1)
        elif grafo.nodes[u]["time"]==2:
            time_de_cada_vertice.append(2)
        else:
            time_de_cada_vertice.append(0)
    
    z=[]
    d=[]
    for u in range(len(grafo.nodes)):
        z.append(0)
        d.append(2)

    if z==time_de_cada_vertice:
        nosso_turno_é_o_primeiro=True
    elif d==time_de_cada_vertice:
        nosso_turno_é_o_primeiro=False
        segundo_turno_é_nosso=True
    else:
        nosso_turno_é_o_primeiro=False

    for v in grafo.nodes:
        pesos[v] = grafo.nodes[v]["peso"]
    
    for v in grafo.nodes:
        distancias[v] = nx.single_source_shortest_path_length(grafo, v)
    
    for u in grafo.nodes:
        if not nosso_turno_é_o_primeiro:
            grafo.neighbors(u)
         #
    if nosso_turno_é_o_primeiro:
        lista=list()
        for u in grafo.nodes:
            if grafo[u]["time"]==0:
                lista.append(grafo.nodes[u]["peso"]*distancias[v][u])
    else:
        if segundo_turno_é_nosso:
            dsadsa
        else:
            dsadas
        
        mediana_ponderada=min(sum(lista))
            # mediana ponderada nx.single_source_shortest_path_length(grafo, i) #centro, nosso_turno

#def func_mediana(grafo):
#    for v in 
#               função MEDIANA(grafo)
#               para cada v com time(v) = 0
#               custo(v) ← Σ peso(u) · d(v, u)
#                   ▹ soma sobre todos os vértices u
#               devolva o v de menor custo(v)

#se a gente começa:
#    pega o mais distante
#senão:
#    pega o com mais vizinhos



