import osmnx as ox
import networkx as nx
import numpy as np
import gurobipy as gp
from gurobipy import GRB
import json
import tqdm
import utils.pathfinding
import argparse
import os

parser = argparse.ArgumentParser()

parser.add_argument("-ts", "--totalsplits", help="How many segments to split the solving into")
parser.add_argument("-s", "--segment", help="Which segment is this ")
parser.add_argument("-q", "--query", help="What to search for ")

ts = int(parser.parse_args().totalsplits)
seg = int(parser.parse_args().segment)
query = str(parser.parse_args().query)

single_destinations = {
    'MDW': (-87.7547633,41.7867799),
    'ORD': (-87.851528, 41.984025),
    'CHI': (-87.6424653, 41.8779594)
}

if not query in single_destinations:
    raise ValueError


if seg > ts:
    raise ValueError

if not os.path.exists('./computation_results/budget_paths'):
    os.mkdir('./computation_results/budget_paths')

with open(f'./computation_results/budget_paths/err-{query}-{seg}-{ts}.txt', 'w') as file:
    file.write(f'')

centroids = json.load(open('./data/tract-centroids.json'))
red_nodes = json.load(open('./data/banned_nodes.json'))

centroids = {tract: coords for tract, coords in centroids.items() if list(centroids.keys()).index(tract) in [i for i in range(int(len(centroids)/ts*seg),int(len(centroids)/ts*(seg+1)))]}

## IMPORT CITY
print('Getting city data')
city = ox.graph_from_place('Chicago, IL, USA', network_type='drive')

## ADDING EDGE PROPERTIES
print('Addign edge attributes')
city = ox.speed.add_edge_speeds(city)
city = ox.speed.add_edge_travel_times(city)

## GENERATING IMPORTANT INFO
indexes = {node: i for i, node in enumerate(city.nodes)}
travel_times_dict = nx.get_edge_attributes(city, 'travel_time')

print('Generating incidence matrix')

banned_nodes = json.load(open('./osmnx/data/banned_nodes.json', 'r'))
banned_edges = []
banned_edges_idx = []

path_lengths = json.load(open(f'./computation_results/budget_paths/{query}-{seg}-{ts}.json', 'r')) if os.path.exists(f'./computation_results/budget_paths/{query}-{seg}-{ts}.json') else {}
previous_results = json.load(open(f'./computation_results/initial_paths/{query}-{seg}-{ts}.json', 'r'))

edges = list(city.edges)

n_points = len(city.nodes)
n_edges = len(city.edges)

A = np.zeros((n_points, n_edges))

for i, (u, v, k) in enumerate(edges):
    if u in banned_nodes or v in banned_nodes:
        banned_edges += [(u, v, k)]
        banned_edges_idx += [i]
        pass

    A[indexes[u]][i] = -1
    A[indexes[v]][i] = 1


print('Starting Linear Program logic')
## LINEAR PROGRAM LOGIC

m = gp.Model("lp")
m.Params.LogToConsole = 0
m.Params.Method = 0

weights = [travel_time for edge, travel_time in travel_times_dict.items()]

f = m.addMVar(shape=n_edges, vtype=GRB.CONTINUOUS, lb=0, name="")

lon, lat = single_destinations[query]

final_node = ox.nearest_nodes(city, lon, lat)
f_idx = indexes[final_node]

obj = np.array(weights)@f

m.setObjective(obj, GRB.MINIMIZE)

b = np.zeros(n_points)

m.addConstr(A@f==b)
m.update()

cnstr = m.getConstrs()
cnstr[f_idx].rhs = 1
m.update()

print('Model generated, solving...')
for i in tqdm.trange(len(centroids)):
    
    tract = list(centroids.keys())[i]
    path_lengths[tract] = path_lengths[tract] if tract in path_lengths else {}
    lon, lat = centroids[tract]

    starting_node = ox.nearest_nodes(city, lon, lat)

    s_idx = indexes[starting_node]
    cnstr[s_idx].rhs = -1
    m.update()

    try:
        banned_nodes = int(previous_results[tract]['n_banned_nodes'])
    except:
        with open(f'./computation_results/budget_paths/err-{query}-{seg}-{ts}.txt', 'a+') as file:
            file.write(f'ERR: {tract} -- No previous results,\n')
        continue

    if not banned_nodes:
        path_lengths[tract] = {0: previous_results[tract]['length']}
        cnstr[s_idx].rhs = 0
        continue

    #print(tract, f"# banned nodes: {previous_results[tract][poi_name]['n_banned_nodes']}, og path length: {previous_results[tract][poi_name]['length']}")

    path_lengths[tract] = {banned_nodes: previous_results[tract]['length']}
    
    budget_constraints = [] 
    for budget in list(np.flip([i for i in range(int(previous_results[tract]['n_banned_nodes']))])):
        budget_constraints += [m.addConstr(gp.quicksum(f[i] for i in banned_edges_idx) <= (budget)*2)]

        m.optimize()

        try:
            flows = m.getAttr("X", m.getVars())
        except:
            with open(f'./computation_results/budget_paths/err-{query}-{seg}-{ts}.txt', 'a+') as file:
                file.write(f'ERR: {tract} -- No solution found,\n')
            continue

        objval = m.ObjVal
        
        flowed_edges_idx = []
        flowed_edges = []

        for i in range(len(flows)):
            if flows[i]:
                flowed_edges_idx += [i]

        for i, (u, v, k) in enumerate(city.edges):
            if i in flowed_edges_idx:
                flowed_edges += [(u, v, k)]
        try:
            path, pts = utils.pathfinding.get_edges_and_points(flowed_edges, \
                                        starting_node=starting_node, final_node=final_node)
        except:
            with open(f'./computation_results/budget_paths/err-{query}-{seg}-{ts}.txt', 'a+') as file:
                file.write(f'ERR {seg}: {tract} -- No path found,\n')
            continue

        path_lengths[tract][int(budget)] = objval
        
        json.dump(path_lengths, open(f'./computation_results/budget_paths/{query}-{seg}-{ts}.json', 'w'), indent=2)
    
    cnstr[s_idx].rhs = 0
    m.remove(budget_constraints)
    m.update()


        
