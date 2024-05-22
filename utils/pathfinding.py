def get_edges_and_points(edges: list, starting_node: int, final_node: int) -> list:
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
        
        return all_edges + [matching_edge]