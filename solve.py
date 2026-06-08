import osmnx as ox
import networkx as nx
import numpy as np
import gurobipy as gp
from gurobipy import GRB
import json
import tqdm
import argparse
import os
from time import sleep
from rich.console import Console


parser = argparse.ArgumentParser()
parser.add_argument("--scope", choices=["fixed", "poi", "commutes"], required=True)
parser.add_argument("-s", "--segment", type=int)
parser.add_argument("-ts", "--totalsplits", type=int)
parser.add_argument("--option", help="POI category, for --scope poi")
parser.add_argument("--latitude", type=float, help="destination, for --scope fixed")
parser.add_argument("--longitude", type=float, help="destination, for --scope fixed")
parser.add_argument("--name", help="output label for --scope fixed")
parser.add_argument("--integer", action="store_true")
args = parser.parse_args()

scope = args.scope
seg = args.segment
ts = args.totalsplits

if seg is None and ts is None:
    seg, ts = 0, 1       
elif seg is None or ts is None:
    parser.error("pass both -s/--segment and -ts/--totalsplits, or neither")
elif not 0 <= seg < ts:
    raise ValueError("segment must be in [0, totalsplits)")
if scope == "poi" and not args.option:
    raise ValueError("--scope poi requires --option")
if scope == "fixed" and (args.latitude is None or args.longitude is None):
    raise ValueError("--scope fixed requires --latitude and --longitude")

if scope == "poi":
    label = args.option
elif scope == "commutes":
    label = "commutes"
else:
    label = args.name or f"{args.latitude}_{args.longitude}"


# path reconstruction from the (unordered) edges carrying flow
def get_edges_for_real(edges, start, end):
    matching = [e for e in edges if e[0] == start]
    if len(matching) == 1 and matching[0][1] == end:
        return matching
    for e in matching:
        return get_edges_for_real([x for x in edges if x != e], e[1], end) + [e]

def get_path_nodes(edges, start, end):
    path = get_edges_for_real(edges, start, end)
    path.reverse()
    return [e[0] for e in path] + [end]


# read/write into a results dict that is nested by key (e.g. (tract, poi_name))
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

console = Console()

with console.status("[bold green]Loading computational parameters...") as status:
    console.log(f"Loading city data...")
    centroids = json.load(open("data/tract-centroids.json"))
    camera_nodes = json.load(open("data/banned_nodes.json"))

    tracts = list(centroids)[int(len(centroids) / ts * seg):int(len(centroids) / ts * (seg + 1))]
    console.log(f"Finished loading city data!")
    
    ## IMPORT CITY
    console.log("Loading road network data (takes a while)...")
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
    camera_edges_idx = []
    for i, (u, v, k) in enumerate(edges):
        if u in camera_nodes or v in camera_nodes:
            camera_edges_idx.append(i)
        A[indexes[u]][i] = -1
        A[indexes[v]][i] = 1

    console.log("Finished generating incidence matrix!")
    

## ENUMERATING (source, sink, key) JOBS FOR THIS SCOPE
def jobs():
    if scope == "fixed":
        sink = ox.nearest_nodes(city, args.longitude, args.latitude)
        for tract in tracts:
            lon, lat = centroids[tract]
            yield ox.nearest_nodes(city, lon, lat), sink, (tract,)
    elif scope == "poi":
        places = json.load(open(f"results/poi/{args.option}.json"))
        for tract in tracts:
            lon, lat = centroids[tract]
            source = ox.nearest_nodes(city, lon, lat)
            for name, coords in places.get(tract, {}).items():
                yield source, ox.nearest_nodes(city, coords[1], coords[0]), (tract, name)
    else:  # commutes
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

console = Console()

with console.status("[bold green]Loading computational parameters...") as status:
    ## LINEAR PROGRAM LOGIC
    console.log("Building Linear Programming model (takes a while)...")
    m = gp.Model("flow")
    m.Params.LogToConsole = 0
    m.Params.Method = 0

    weights = np.array([city.edges[e]["travel_time"] for e in edges])
    f = m.addMVar(shape=n_edges, vtype=GRB.INTEGER if args.integer else GRB.CONTINUOUS, lb=0, name="")
    m.setObjective(weights @ f, GRB.MINIMIZE)
    m.addConstr(A @ f == np.zeros(n_points))
    m.update()
    cnstr = m.getConstrs()
    console.log("Finished building Linear Programming model...")

os.makedirs("results/paths/initial", exist_ok=True)
os.makedirs("results/paths/budget", exist_ok=True)
initial_file = f"results/paths/initial/{label}-{seg}-{ts}.json"
budget_file = f"results/paths/budget/{label}-{seg}-{ts}.json"
initial = json.load(open(initial_file)) if os.path.exists(initial_file) else {}
budget = json.load(open(budget_file)) if os.path.exists(budget_file) else {}

print("Model generated, solving...")
for source, sink, key in tqdm.tqdm(all_jobs):
    cnstr[indexes[source]].rhs = -1
    cnstr[indexes[sink]].rhs = 1
    m.update()

    # initial, unconstrained pass: shortest path and the cameras on it
    if lookup(initial, key) is not None:
        cameras = lookup(initial, key)["n_banned_nodes"]
    else:
        m.optimize()
        if m.Status != GRB.OPTIMAL:
            cnstr[indexes[source]].rhs = 0
            cnstr[indexes[sink]].rhs = 0
            continue
        x = f.X                                    
        flowed = [edges[i] for i in np.flatnonzero(x)]
        try:
            pts = get_path_nodes(flowed, source, sink)
        except Exception:
            cnstr[indexes[source]].rhs = 0
            cnstr[indexes[sink]].rhs = 0
            continue
        cameras = len([p for p in pts if p in camera_nodes])
        store(initial, key, {"length": m.ObjVal, "n_banned_nodes": cameras})
        json.dump(initial, open(initial_file, "w"), indent=2)

    # budgets pass: re-solve allowing fewer and fewer cameras
    levels = {str(cameras): lookup(initial, key)["length"]}
    constraints = []
    for b in range(cameras - 1, -1, -1):
        constraints.append(m.addConstr(gp.quicksum(f[i] for i in camera_edges_idx) <= b * 2))
        m.optimize()
        if m.Status == GRB.OPTIMAL:
            levels[str(b)] = m.ObjVal
    for c in constraints:
        m.remove(c)
    store(budget, key, levels)
    json.dump(budget, open(budget_file, "w"), indent=2)

    cnstr[indexes[source]].rhs = 0
    cnstr[indexes[sink]].rhs = 0
    m.update()
