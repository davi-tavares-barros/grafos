#utilizei o teste 3 e fui ajustando viu galera

import networkx as nx


def calcular_saldo(grafo, centros_nossos, centros_adv, pesos):
    dist_n = (
        nx.multi_source_dijkstra_path_length(grafo, centros_nossos, weight=None)
        if centros_nossos
        else {}
    )
    dist_a = (
        nx.multi_source_dijkstra_path_length(grafo, centros_adv, weight=None)
        if centros_adv
        else {}
    )

    total_n = 0.0
    total_a = 0.0

    for no in grafo.nodes:
        dn = dist_n.get(no, float("inf"))
        da = dist_a.get(no, float("inf"))

        if dn == float("inf") and da == float("inf"):
            continue
        if dn < da:
            total_n += pesos[no]
        elif da < dn:
            total_a += pesos[no]
        else:
            total_n += pesos[no] / 2
            total_a += pesos[no] / 2

    return total_n - total_a


def pontuar_candidatos(grafo, livres, lista_nossa, lista_adversario, pesos):
    pontos = {v: 0.0 for v in livres}

    for v in livres:
        nossos_centros = lista_nossa + [v]
        dist_n = nx.multi_source_dijkstra_path_length(grafo, nossos_centros, weight=None)
        dist_a = (
            nx.multi_source_dijkstra_path_length(grafo, lista_adversario, weight=None)
            if lista_adversario
            else {}
        )

        for u in grafo.nodes:
            dn = dist_n.get(u, float("inf"))
            da = dist_a.get(u, float("inf"))

            if dn == float("inf") and da == float("inf"):
                continue
            if dn == da:
                pontos[v] += pesos[u] / 2
            elif dn < da:
                pontos[v] += pesos[u]

    return pontos


def melhor_resposta_adversario(grafo, restantes, nossos_centros, lista_adversario, pesos):
    #ele vai escolher a jogada que minimiza o nosso saldo (pior cenário real para gente)
    pior_saldo_para_nos = None
    melhor_w = None

    for w in restantes:
        saldo_apos_w = calcular_saldo(grafo, nossos_centros, lista_adversario + [w], pesos)
        if pior_saldo_para_nos is None or saldo_apos_w < pior_saldo_para_nos:
            pior_saldo_para_nos = saldo_apos_w
            melhor_w = w

    return melhor_w, pior_saldo_para_nos


def potencial_regiao(grafo, u, pesos):
    #ele soma o peso do próprio vértice com os vizinhos diretos (alcance imediato)
    return pesos[u] + sum(pesos[viz] for viz in grafo.neighbors(u))


#VORONOI_ESTRATEGIA
def estrategia(grafo):

    #busca os dados do grafo
    pesos = {v: grafo.nodes[v]["peso"] for v in grafo.nodes}
    livres = [v for v in grafo.nodes if grafo.nodes[v]["time"] == 0]
    lista_nossa = [v for v in grafo.nodes if grafo.nodes[v]["time"] == 1]
    lista_adversario = [v for v in grafo.nodes if grafo.nodes[v]["time"] == 2]

    #se n nenhum vértice, não tem jogada
    if not livres:
        return None

    #vê nossa quantidade e do adv
    qtd_nossa = len(lista_nossa)
    qtd_adv = len(lista_adversario)

    #abertura (0x0): utiliza a mediana ponderada + relevância estrutural normalizada
    if qtd_adv == 0 and qtd_nossa == 0:
        #utiliza vários métodos do networkx para calcular dados estruturais do grafo
        distancias = {v: nx.single_source_shortest_path_length(grafo, v) for v in grafo.nodes}
        gargalos = set(nx.articulation_points(grafo))
        nos_em_pontes = {u for p in nx.bridges(grafo) for u in p}
        centralidade = nx.betweenness_centrality(grafo)

        melhor_chave = None
        escolha = None
        for u in livres:
            #vai penalizar os vértices isolados em componentes pequenos e minimiza distância ponderada
            alcancaveis = distancias[u]
            peso_alcancavel = sum(pesos[no] for no in alcancaveis)
            custo_u = sum(pesos[no] * dist for no, dist in alcancaveis.items())

            score_estrutural = (
                centralidade.get(u, 0.0)
                + (0.05 if u in gargalos else 0.0)
                + (0.05 if u in nos_em_pontes else 0.0)
            )
            chave_u = (peso_alcancavel, -custo_u, score_estrutural, potencial_regiao(grafo, u, pesos))
            if melhor_chave is None or chave_u > melhor_chave:
                melhor_chave = chave_u
                escolha = u
        return escolha

    #ultima jogada sem resposta do adversário dps (3x2): maximiza nosso ganho final
    if qtd_adv == 3 and qtd_nossa == 2:
        pontos = pontuar_candidatos(grafo, livres, lista_nossa, lista_adversario, pesos)
        return max(pontos, key=lambda v: (pontos[v], potencial_regiao(grafo, v, pesos)))

    #demais rodadas: minimax de 1 passo baseado no saldo da partida
    melhor_chave = None
    escolha = None
    for u in livres:
        nossos_pos_u = lista_nossa + [u]
        restantes = [x for x in livres if x != u]

        if qtd_adv < 3 and restantes:
            #descarta o primeiro retorno
            _, saldo_garantido = melhor_resposta_adversario(
                grafo, restantes, nossos_pos_u, lista_adversario, pesos
            )
        else:
            saldo_garantido = calcular_saldo(grafo, nossos_pos_u, lista_adversario, pesos)

        ganho_imediato = pontuar_candidatos(grafo, [u], lista_nossa, lista_adversario, pesos)[u]
        chave = (saldo_garantido, ganho_imediato, potencial_regiao(grafo, u, pesos))

        if melhor_chave is None or chave > melhor_chave:
            melhor_chave = chave
            escolha = u

    return escolha