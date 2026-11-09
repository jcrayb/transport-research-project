import osmnx as ox
import numpy as np
import gurobipy as gp
from gurobipy import GRB
import json
import tqdm
import argparse
import os
from rich.console import Console

# Solves the unrestricted (no camera budget) shortest path problem for every
# commute origin-destination pair, exactly as in solve.py, and reports how the
# travel time splits between highways and city streets.
# Only writes to results/paths/budget/commutes-road-breakdown.json.

parser = argparse.ArgumentParser()
parser.add_argument("-s", "--segment", type=int, default=0)
parser.add_argument("-ts", "--totalsplits", type=int, default=1)
parser.add_argument("--integer", action="store_true")
args = parser.parse_args()

seg = args.segment
ts = args.totalsplits

HIGHWAY_TAGS = {"motorway", "motorway_link", "trunk", "trunk_link"}


def is_highway(tag):
    # osmnx stores merged ways as lists (or their string repr when loaded from graphml)
    if isinstance(tag, list):
        return any(t in HIGHWAY_TAGS for t in tag)
    return any(t in str(tag) for t in HIGHWAY_TAGS)


# read/write into a results dict that is nested by key (e.g. (tract, dest))
def store(tree, key, value):
    for part in key[:-1]:
        tree = tree.setdefault(part, {})
    tree[key[-1]] = value

def lookup(tree, key):
    for part in key:
        if not isinstance(tree, dict) or part not in tree:
            return None
        tree = tree[part]
    return tree

GRAPH_FILE = "data/1.gpkg"

console = Console()

with console.status("[bold green]Loading computational parameters...") as status:
    console.log(f"Loading city data...")
    centroids = json.load(open("data/tract-centroids.json"))

    tracts = list(centroids)[int(len(centroids) / ts * seg):int(len(centroids) / ts * (seg + 1))]
    console.log(f"Finished loading city data!")

    ## IMPORT CITY
    console.log("Loading road network data (takes a while)...")
    if os.path.exists(GRAPH_FILE):
        city = ox.load_graphml(GRAPH_FILE)
    else:
        city = ox.graph_from_place("Chicago, IL, USA", network_type="drive")

        ## ADDING EDGE PROPERTIES
        city = ox.add_edge_speeds(city)
        city = ox.add_edge_travel_times(city)
    console.log("Finished loading road network data!")

    ## GENERATING IMPORTANT INFO
    console.log("Generating incidence matrix...")
    indexes = {node: i for i, node in enumerate(city.nodes)}
    edges = list(city.edges)
    n_points = len(city.nodes)
    n_edges = len(edges)

    ## GENERATING INCIDENCE MATRIX
    A = np.zeros((n_points, n_edges))
    for i, (u, v, k) in enumerate(edges):
        A[indexes[u]][i] = -1
        A[indexes[v]][i] = 1

    console.log("Finished generating incidence matrix!")

## ENUMERATING (source, sink, key) COMMUTE JOBS
def jobs():
    pairs = json.load(open("data/origin_pairs.json"))

    all_tracts = list(centroids)
    node_ids = ox.nearest_nodes(city,
                                [centroids[t][0] for t in all_tracts],
                                [centroids[t][1] for t in all_tracts])
    tract_nodes = {t: int(n) for t, n in zip(all_tracts, node_ids)}
    for tract in tracts:
        if tract not in pairs:
            continue
        for dest in np.unique(pairs[tract]):
            yield tract_nodes[tract], tract_nodes[str(dest)], (tract, str(dest))

all_jobs = list(jobs())

penalty_time = 0

with console.status("[bold green]Loading computational parameters...") as status:
    ## LINEAR PROGRAM LOGIC
    console.log("Building Linear Programming model (takes a while)...")
    m = gp.Model("flow")
    m.Params.LogToConsole = 0
    m.Params.Method = 0

    # per-edge signal penalty: penalty_time/2 if either endpoint has a signal, else 0
    signal_dict = json.load(open('data/signal_nodes.json', 'r'))
    c = np.array([penalty_time / 2 if signal_dict[str(u)] or signal_dict[str(v)] else 0
                  for u, v, k in edges])
    travel_times = np.array([city.edges[e]["travel_time"] for e in edges])
    weights = travel_times + c
    highway_mask = np.array([is_highway(city.edges[e].get("highway")) for e in edges])

    f = m.addMVar(shape=n_edges, vtype=GRB.INTEGER if args.integer else GRB.CONTINUOUS, lb=0, name="")
    m.setObjective(weights @ f, GRB.MINIMIZE)
    m.addConstr(A @ f == np.zeros(n_points))
    m.update()
    cnstr = m.getConstrs()
    console.log("Finished building Linear Programming model...")

os.makedirs("results/paths/budget", exist_ok=True)
suffix = "" if ts == 1 else f"-{seg}-{ts}"
out_file = f"results/paths/initial/commutes-road-breakdown{suffix}_{penalty_time}s.json"
# resume from a previous run of this script (never touches solve.py's outputs)
breakdown = json.load(open(out_file)) if os.path.exists(out_file) else {}

print("Model generated, solving...")
for source, sink, key in tqdm.tqdm(all_jobs):
    if lookup(breakdown, key) is not None:
        continue

    cnstr[indexes[source]].rhs = -1
    cnstr[indexes[sink]].rhs = 1
    m.update()

    m.optimize()
    if m.Status == GRB.OPTIMAL:
        x = f.X
        store(breakdown, key, {
            "highway_time": float(travel_times[highway_mask] @ x[highway_mask]),
            "city_time": float(travel_times[~highway_mask] @ x[~highway_mask]),
            "signal_penalty": float(c @ x),
            "length": m.ObjVal,
        })
        json.dump(breakdown, open(out_file, "w"), indent=2)

    cnstr[indexes[source]].rhs = 0
    cnstr[indexes[sink]].rhs = 0
    m.update()
