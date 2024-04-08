import osmnx as ox

## IMPORT CITY
print('Getting city data')
city = ox.graph_from_place('Chicago, IL, USA', network_type='drive')

import networkx as nx
import numpy as np

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
import gurobipy as gp
from gurobipy import GRB
import json
import tqdm
import utils

unrestricted_path_lengths = {}

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
print('Model generated, solving...')
for i in tqdm.trange(len(centroids)):
    tract = list(centroids.keys())[i]
    unrestricted_path_lengths[tract] = {}
    lon, lat = centroids[tract]

    starting_node = ox.nearest_nodes(city, lon, lat)
    b = np.zeros(n_points)
    b[indexes[starting_node]] = -1
    b[indexes[final_node]] = 1


    m.remove(m.getConstrs())
    m.addConstr(A@f==b)

    m.optimize()

    flows = m.getAttr("X", m.getVars())

    objval = m.ObjVal
    
    unrestricted_path_lengths[tract]['length']=objval
    flowed_edges_idx = []
    flowed_edges = []

    for i in range(len(flows)):
        if flows[i]:
            flowed_edges_idx += [i]

    for i, (u, v, k) in enumerate(city.edges):
        if i in flowed_edges_idx:
            flowed_edges += [(u, v, k)]
    
    path, pts = utils.get_edges_and_points(flowed_edges, starting_node=starting_node, final_node=final_node)
    unrestricted_path_lengths[tract]['n_banned_nodes'] = len([pt for pt in pts if pt in red_nodes])
    continue

json.dump(unrestricted_path_lengths, open('./results.json'))
