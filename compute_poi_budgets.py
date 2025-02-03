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

query = 'high-school'

parser = argparse.ArgumentParser()

parser.add_argument("-ts", "--totalsplits", help="How many segments to split the solving into")
parser.add_argument("-s", "--segment", help="Which segment is this ")

ts = int(parser.parse_args().totalsplits)
seg = int(parser.parse_args().segment)

if seg > ts:
    raise ValueError

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

places_of_interest = json.load(open(f'./computation_results/{query}.json'))

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

path_lengths = json.load(open(f'./computation_results/budget_paths/{query}-{seg}-{ts}.json', 'r')) if os.path.exists(f'./computation_results/budget_paths/{query}-{seg}-{ts}.json') else {}
previous_results = json.load(open(f'./computation_results/initial_paths/{query}-{seg}-{ts}.json', 'r'))

obj = np.array(weights)@f

m.setObjective(obj, GRB.MINIMIZE)

print('Model generated, solving...')
for i in tqdm.trange(len(centroids)):
    
    tract = list(centroids.keys())[i]
    path_lengths[tract] = path_lengths[tract] if tract in path_lengths else {}
    lon, lat = centroids[tract]

    starting_node = ox.nearest_nodes(city, lon, lat)
    for poi_name, poi_coords in places_of_interest[tract].items():
        
        if poi_name in path_lengths[tract]:
            continue

        try:
            banned_nodes = int(previous_results[tract][poi_name]['n_banned_nodes'])
        except:
            with open(f'./computation_results/budget_paths/err-{query}-{seg}-{ts}.txt', 'a+') as file:
                file.write(f'ERR: {tract} {poi_name} -- No previous results,\n')
            continue

        if not banned_nodes:
            path_lengths[tract][poi_name] = {0: previous_results[tract][poi_name]['length']}
            continue

        #print(tract, f"# banned nodes: {previous_results[tract][poi_name]['n_banned_nodes']}, og path length: {previous_results[tract][poi_name]['length']}")

        path_lengths[tract][poi_name] = {banned_nodes: previous_results[tract][poi_name]['length']}
        
        lat2, lon2 = (poi_coords[0], poi_coords[1])

        final_node = ox.nearest_nodes(city, lon2, lat2)

        b = np.zeros(n_points)
        b[indexes[starting_node]] = -1
        b[indexes[final_node]] = 1


        m.remove(m.getConstrs())
        m.addConstr(A@f==b)
        for budget in list(np.flip([i for i in range(int(previous_results[tract][poi_name]['n_banned_nodes']))])):
            m.addConstr(gp.quicksum(f[i] for i in banned_edges_idx) <= (budget)*2)

            m.optimize()

            try:
                flows = m.getAttr("X", m.getVars())
            except:
                with open(f'./computation_results/budget_paths/err-{query}.txt', 'a+') as file:
                    file.write(f'ERR: {tract} {poi_name} -- No solution found,\n')
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
                with open(f'./computation_results/budget_paths/err-{query}.txt', 'a+') as file:
                    file.write(f'ERR {seg}: {tract} {poi_name} -- No path found,\n')
                continue

            path_lengths[tract][poi_name][int(budget)] = objval
            
            json.dump(path_lengths, open(f'./computation_results/budget_paths/{query}-{seg}-{ts}.json', 'w'), indent=2)
            continue

        
