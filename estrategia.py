import networkx as nx

#def estrategia():
#    gargalos = list(nx.articulation_points(grafo))
#    pontes = list(nx.bridges(grafo))
#    centralidade = nx.betweenness_centrality(grafo)


def VERTICES(grafo):
    livres = [v for v in grafo.nodes if grafo.nodes[v]["time"] == 0]
    lista_nossa = [v for v in grafo.nodes if grafo.nodes[v]["time"] == 1]
    lista_adversário = [v for v in grafo.nodes if grafo.nodes[v]["time"] == 2]
    return livres, lista_nossa, lista_adversário


def PESOS(grafo):
    pesos={v:0 for v in grafo.nodes}
    for v in grafo.nodes:
        #lista dos pesos
        pesos[v] = grafo.nodes[v]["peso"]
    return pesos


def DISTANCIAS(grafo):
    distancias={v:0 for v in grafo.nodes}
    for v in grafo.nodes:
        #lista das distâncias
        distancias[v] = nx.single_source_shortest_path_length(grafo, v)
    return distancias

def PONTOS(grafo):   #GANHO IMEDIATO
    pesos=PESOS(grafo)
    distancias=DISTANCIAS(grafo)
    livres, lista_nossa, lista_adversário=VERTICES(grafo)
    pontos={v:0 for v in livres}

    for v in livres:    #GANHO IMEDIATO
        distancias_dos_nossos_vertices=nx.multi_source_dijkstra_path_length(grafo, lista_nossa + [v], weight=None)
        if len(lista_adversário)!=0:
            distancias_dos_vertices_adversário=nx.multi_source_dijkstra_path_length(grafo, lista_adversário, weight=None)
        else:
            distancias_dos_vertices_adversário=None
        for u in grafo.nodes:
            distancia_nossa_atual=distancias_dos_nossos_vertices[u]
            distancias_adversário_atual=distancias_dos_vertices_adversário[u] if distancias_dos_vertices_adversário is not None else float("inf")
            if distancia_nossa_atual==distancias_adversário_atual:
                pontos[v]+=pesos[u]/2
            elif distancia_nossa_atual<distancias_adversário_atual:
                pontos[v]+=pesos[u]    
    return pontos


def dados_estruturais(grafo):
    dsadas


def ganho_imediato(grafo):
    #distancias=distancias(grafo)
    

    #livres, lista_nossa, lista_adversário=vertices(grafo)
    #livres = [v for v in grafo.nodes if grafo.nodes[v]["time"] == 0]
    #lista_nossa = [v for v in grafo.nodes if grafo.nodes[v]["time"] == 1]
    #lista_adversário = [v for v in grafo.nodes if grafo.nodes[v]["time"] == 2]

    #for v in  livres:
    #    for u in grafo.nodes:
    #        a=min([i for i in distancias[v][u] if v in livres])
    #        b=min([i for i in distancias[v][u] if v in lista_adversário])
    #        if a<b:
    #            total+=pesos[u]
    for i in PONTOS(grafo):
        if PONTOS(grafo)[i]==max(PONTOS(grafo).values):
            return 

    #deles ← { c : time(c) = 2 }
    #para cada v com time(v) = 0
    #    ganho(v) ← PONTOS(meus ∪ {v}, deles)
    #devolva o v de maior ganho(v)

#função PONTOS(meus, deles)
#    total ← 0
#    para cada vértice u
#        a ← min { d(c, u) : c ∈ meus }
#        b ← min { d(c, u) : c ∈ deles }
#        se a < b então total ← total + peso(u)
#        senão se a = b < ∞ então
#            total ← total + peso(u)/2
#    devolva total

#▹ o mínimo de um conjunto vazio é ∞


def ESTRATEGIA(grafo):
    pesos=PESOS(grafo)
    distancias={}
    gargalos = list(nx.articulation_points(grafo))
    pontes = list(nx.bridges(grafo))
    centralidade = nx.betweenness_centrality(grafo)
    livres, lista_nossa, lista_adversário = VERTICES(grafo)

    if len(lista_adversário)==len(lista_nossa):
        #a gente começou a jogar.
        if len(lista_adversário)==0 and len(lista_nossa)==0:
            #nossa primeira jogada.
            for u in livres:

        elif len(lista_adversário)==1 and len(lista_nossa)==1:
            #nossa segunda jogada
            for u in livres:
        elif len(lista_adversário)==2 and len(lista_nossa)==2:
            #nossa terceira jogada
            for u in livres:
        
    else:
        #o adversário que começou.
        if len(lista_adversário)==1 and len(lista_nossa)==0:
            #nossa primeira jogada.
            for u in livres:
        elif len(lista_adversário)==2 and len(lista_nossa)==1:
            #segunda jogada
            for u in livres:
        elif len(lista_adversário)==3 and len(lista_nossa)==2:
            #nossa terceira jogada
            for u in livres:
        

    

    
    #for u in grafo.nodes:
    #    if not nosso_turno_é_o_primeiro:
    #        grafo.neighbors(u)
           

    #if nosso_turno_é_o_primeiro:
    #    lista=list()
    #    for u in grafo.nodes:
    #        if grafo[u]["time"]==0:
    #            lista.append(grafo.nodes[u]["peso"]*distancias[v][u])
    #    mediana_ponderada=min(sum(lista))
    #else:
    #    if segundo_turno_é_nosso:
    #        dsadsa
    #    else:
    #        dsadas


        
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



