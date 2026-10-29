import osmnx as ox
import networkx as nx
import numpy as np
import json
import tqdm
from rich.console import Console


def get_num_signals(city, nodes_visited):
    def has_signal(node):
        attrs = city.nodes[node]
        if not 'highway' in attrs:
            return False
        elif attrs['highway'] == "traffic_signals":
            return True
        else:
            return False

    num_signals = sum([has_signal(p) for p in nodes_visited])
    return num_signals


console = Console()

with console.status("[bold green]Loading computational parameters...") as status:
    console.log("Loading city data...")
    centroids = json.load(open("data/tract-centroids.json"))
    pairs = json.load(open("data/origin_pairs.json"))
    console.log("Finished loading city data!")

    ## IMPORT CITY
    console.log("Loading road network data (takes a while)...")
    city = ox.graph_from_place("Chicago, IL, USA", network_type="drive")

    ## ADDING EDGE PROPERTIES
    city = ox.add_edge_speeds(city)
    city = ox.add_edge_travel_times(city)
    console.log("Finished loading road network data!")

    ## SNAPPING TRACT CENTROIDS TO THE ROAD NETWORK
    all_tracts = list(centroids)
    node_ids = ox.nearest_nodes(city,
                                [centroids[t][0] for t in all_tracts],
                                [centroids[t][1] for t in all_tracts])
    tract_nodes = {t: int(n) for t, n in zip(all_tracts, node_ids)}

output_file = "data/num_traffic_signals.json"
results = {}

for tract in tqdm.tqdm(pairs):
    if tract not in tract_nodes:
        continue
    # one Dijkstra per origin gives the shortest (travel time) path to every destination
    paths = nx.single_source_dijkstra_path(city, tract_nodes[tract], weight="travel_time")
    for dest in np.unique(pairs[tract]):
        dest = str(dest)
        if dest not in tract_nodes or tract_nodes[dest] not in paths:
            continue
        num_signals = get_num_signals(city, paths[tract_nodes[dest]])
        results.setdefault(tract, {})[dest] = int(num_signals)

json.dump(results, open(output_file, "w"), indent=2)
console.log(f"Saved traffic signal counts to {output_file}")
