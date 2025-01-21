import osmnx as ox
import networkx as nx
import numpy as np
import tqdm
import gurobipy as gp
from gurobipy import GRB
import json
import utils.pathfinding
import argparse
import os

parser = argparse.ArgumentParser()

parser.add_argument("-ts", "--totalsplits", help="How many segments to split the solving into")
parser.add_argument("-s", "--segment", help="Which segment is this ")

ts = int(parser.parse_args().totalsplits)
seg = int(parser.parse_args().segment)

if not seg:
    raise ValueError('Segments are One-indexed')

if seg > ts:
    raise ValueError

with open(f'./computation_results/initial_paths/err-{seg}-{ts}.txt', 'w+') as file:
    file.write(f'')

all_tracts = json.load(open('./data/tract-centroids.json'))
red_nodes = json.load(open('./data/banned_nodes.json'))

tracts = {tract: coords for tract, coords in all_tracts.items() if list(all_tracts.keys()).index(tract) in [i for i in range(int(len(all_tracts)/ts*(seg-1)),int(len(all_tracts)/ts*(seg)))]}

## IMPORT CITY
print('Getting city data')
city = ox.graph_from_place('Chicago, IL, USA', network_type='drive')

## ADDING EDGE PROPERTIES
print('Addign edge attributes')
city = ox.add_edge_speeds(city)
city = ox.add_edge_travel_times(city)

## GENERATING IMPORTANT INFO
indexes = {node: i for i, node in enumerate(city.nodes)}
travel_times_dict = nx.get_edge_attributes(city, 'travel_time')

print('Generating incidence matrix')

banned_nodes = []
banned_edges = []
banned_edges_idx = []

origin_pairs = json.load(open(f'./data/origin_pairs.json'))

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
if not os.path.exists('./computation_results/weighted'):
    os.mkdir('./computation_results/weighted')

previous_results = json.load(open(f'./computation_results/weighted/initial-{seg}-{ts}.json', 'r')) if os.path.exists(f'./computation_results/initial_paths/initial-{seg}-{ts}.json') else {}
unrestricted_path_lengths = {} 

nodes_numbers = json.load(open(f'./data/tract-node#.json', 'r'))

m = gp.Model("lp")
m.Params.LogToConsole = 0
m.Params.Method = 0

weights = [travel_time for edge, travel_time in travel_times_dict.items()]

f = m.addMVar(shape=n_edges, vtype=GRB.INTEGER, lb=0, name="")

obj = np.array(weights)@f

m.setObjective(obj, GRB.MINIMIZE)

b = np.zeros(n_points)

m.addConstr(A@f==b)
m.update()

cnstr = m.getConstrs()
print('Model generated, solving...')
for i in tqdm.trange(len(tracts)):
    origin_tract = list(tracts.keys())[i]

    if not origin_tract in origin_pairs: continue

    unrestricted_path_lengths[origin_tract] = {}

    starting_node = nodes_numbers[origin_tract]

    s_idx = indexes[starting_node]
    
    cnstr[s_idx].rhs = -1
    m.update()

    for dest_tract in np.unique(origin_pairs[origin_tract]):
        
        if origin_tract in previous_results:
            if dest_tract in previous_results[origin_tract]:
                unrestricted_path_lengths[origin_tract][dest_tract] = previous_results[origin_tract][dest_tract]
                continue
            
        unrestricted_path_lengths[origin_tract][dest_tract] = {}

        final_node = nodes_numbers[dest_tract]

        f_idx = indexes[final_node]

        cnstr[f_idx].rhs = 1
        m.update()
        m.write('./debug.lp')
        
        m.optimize()

        cnstr[f_idx].rhs = 0
        
        try:
            flows = m.getAttr("X", m.getVars())
        except Exception as e:
            with open(f'./computation_results/weighted/err-init-{seg}-{ts}.txt', 'a+') as file:
                file.write(f'ERR: {origin_tract} {dest_tract} -- No solution found, {e}\n')
            continue

        objval = m.ObjVal

        flowed_edges_idx = []
        flowed_edges = []

        for i in range(len(flows)):
            if flows[i]:
                flowed_edges_idx.append(i)

        for i, (u, v, k) in enumerate(city.edges):
            if i in flowed_edges_idx:
                flowed_edges.append((u, v, k))
        try:
            path, pts = utils.pathfinding.get_edges_and_points(flowed_edges, \
                                        starting_node=starting_node, final_node=final_node)
        except:
            with open(f'./computation_results/weighted/err-init-{seg}-{ts}.txt', 'a+') as file:
                file.write(f'ERR {seg}: {origin_tract} {dest_tract} -- No path found, {str((starting_node, final_node))}, {str(flowed_edges)}\n')
            continue

        unrestricted_path_lengths[origin_tract][dest_tract]['n_banned_nodes'] = len([pt for pt in pts if pt in red_nodes])
        unrestricted_path_lengths[origin_tract][dest_tract]['length'] = objval
        
        json.dump(unrestricted_path_lengths, open(f'./computation_results/weighted/initial-{seg}-{ts}.json', 'w'), indent=2)
        
    
    cnstr[s_idx].rhs = 0
        
