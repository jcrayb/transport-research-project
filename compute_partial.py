import osmnx as ox
import networkx as nx
import numpy as np
import tqdm
import gurobipy as gp
from gurobipy import GRB
import json
import tqdm
import utils

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

banned_nodes = []
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

path_lengths = {}

centroids = json.load(open('./data/tract-centroids.json'))
red_nodes = json.load(open('./data/banned_nodes.json'))

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
    1: [],
    2: [1],
    3: [1, 2],
    4: [1, 2, 3],
    5: [2, 3, 4],
    6: [2, 3, 5],
    7: [2, 4, 6],
    8: [2, 4, 6],
    9: [3, 5, 7],
    10: [3, 5, 8]
}

previous_results = json.load(open('./results.json', 'r'))

print('Model generated, solving...')
for i in tqdm.trange(len(centroids)):
    tract = list(centroids.keys())[i]
    path_lengths[tract] = {}
    lon, lat = centroids[tract]

    starting_node = ox.nearest_nodes(city, lon, lat)
    b = np.zeros(n_points)
    b[indexes[starting_node]] = -1
    b[indexes[final_node]] = 1


    m.remove(m.getConstrs())
    m.addConstr(A@f==b)

    budgets = max_budgets[previous_results[tract]['n_banned_nodes']]

    for budget in list(np.flip(budgets)):
        m.addConstr(gp.quicksum(f[i] for i in banned_edges_idx) <= (budget)*2)

        m.optimize()

        flows = m.getAttr("X", m.getVars())

        objval = m.ObjVal
        
        '''path_lengths[tract][budget]=objval
        flowed_edges_idx = []
        flowed_edges = []

        for i in range(len(flows)):
            if flows[i]:
                flowed_edges_idx += [i]

        for i, (u, v, k) in enumerate(city.edges):
            if i in flowed_edges_idx:
                flowed_edges += [(u, v, k)]
        
        path, pts = utils.get_edges_and_points(flowed_edges, starting_node=starting_node, final_node=final_node)'''
        
        continue
    json.dump(path_lengths, open('./results_partial.json', 'w'))


