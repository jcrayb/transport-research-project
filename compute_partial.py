import osmnx as ox
import networkx as nx
import numpy as np
import tqdm
import gurobipy as gp
from gurobipy import GRB
import json
import tqdm
import utils.main as main

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

centroids = json.load(open('./data/tract-centroids.json'))

final_node = ox.nearest_nodes(city, -87.851528, 41.984025)

m = gp.Model("lp")
m.Params.LogToConsole = 0
m.Params.Method = 0

weights = [travel_time for edge, travel_time in travel_times_dict.items()]

f = m.addMVar(shape=n_edges, vtype=GRB.INTEGER, lb=0, name="")

obj = np.array(weights)@f

m.setObjective(obj, GRB.MINIMIZE)

##MAX BUDGET DICT

max_budgets = {0: [],
    1: [0],
    2: [0, 1],
    3: [0, 1, 2],
    4: [0, 1, 2, 3],
    5: [0, 2, 3, 4],
    6: [0, 2, 3, 5],
    7: [0, 2, 4, 6],
    8: [0, 2, 4, 6],
    9: [0, 3, 5, 7],
    10: [0, 3, 5, 8]
}

previous_results = json.load(open('./results.json', 'r'))
path_lengths = json.load(open('./results_partial.json', 'r'))
print(len(path_lengths))
with open('log.txt', 'w') as file:
    file.write('')

print('Model generated, solving...')
for i in tqdm.trange(len(centroids)):
    tract = list(centroids.keys())[i]

    budgets = max_budgets[previous_results[tract]['n_banned_nodes']]

    if not budgets: continue
    if tract in path_lengths: continue
    
    print(tract, f"# banned nodes: {previous_results[tract]['n_banned_nodes']}, og path length: {previous_results[tract]['length']}")
    path_lengths[tract] = {}
    lon, lat = centroids[tract]
    
    starting_node = ox.nearest_nodes(city, lon, lat)
    b = np.zeros(n_points)
    b[indexes[starting_node]] = -1
    b[indexes[final_node]] = 1


    m.remove(m.getConstrs())
    m.addConstr(A@f==b)

    

    for budget in list(np.flip([i for i in range(previous_results[tract]['n_banned_nodes'])])):
        m.addConstr(gp.quicksum(f[i] for i in banned_edges_idx) <= (budget)*2)
        
        m.optimize()
        try:
            flows = m.getAttr("X", m.getVars())
        except:
            with open('log.txt', 'a') as file:
                file.write(f'ERR: {tract}')
            continue
        objval = m.ObjVal
        print('Budget: ', budget, "Path length: ", objval)

        path_lengths[tract][int(budget)] = objval
        continue
    json.dump(path_lengths, open('./results_partial.json', 'w'))


