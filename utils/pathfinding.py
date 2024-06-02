'''def get_edges_and_points(edges: list, starting_node: int, final_node: int) -> list:
    path = get_edges_for_real(edges, starting_node, final_node)
    path.reverse()
    pts = [edge[0] for edge in path] + [final_node]
    return path, pts

def get_edges_for_real(edges: list, starting_node: int, final_node: int) -> list:
    matching_edges = [edge for edge in edges if edge[0] == starting_node]

    if len(matching_edges) == 1 and matching_edges[0][1] == final_node:
        return matching_edges

    for matching_edge in matching_edges:
        all_edges = get_edges_for_real([edge for edge in edges if edge != matching_edge], matching_edge[1], final_node)
        
        return all_edges + [matching_edge]'''

import networkx as nx
import numpy as np

def get_edges_and_points(edges, starting_node, final_node):
    G = nx.DiGraph()

    nodes = []

    for edge in edges:
        nodes += [edge[0], edge[1]]

    nodes = np.unique(nodes)

    G.add_nodes_from(nodes)
    G.add_edges_from([(edge[0], edge[1]) for edge in edges])

    path = nx.single_source_shortest_path(G, starting_node)
    return path[final_node]