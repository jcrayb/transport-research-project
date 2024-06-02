import osmnx as ox
import networkx as nx
import numpy as np
import tqdm
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

if not query:
    raise ValueError

if seg > ts:
    raise ValueError

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

banned_nodes = []
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

previous_results = json.load(open(f'./computation_results/initial_paths/{query}-{seg}-{ts}.json', 'r')) if os.path.exists(f'./computation_results/initial_paths/{query}-{seg}-{ts}.json') else {}

unrestricted_path_lengths = {}

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

    if not tract in places_of_interest:
        continue
    
    for poi_name, poi_coords in places_of_interest[tract].items():
        
        if tract in previous_results:
            if poi_name in previous_results[tract]:
                print(tract, poi_name)
                unrestricted_path_lengths[tract][poi_name] = previous_results[tract][poi_name]
                continue
            
        unrestricted_path_lengths[tract][poi_name] = {}

        lat2, lon2 = (poi_coords[0], poi_coords[1])

        final_node = ox.nearest_nodes(city, lon2, lat2)

        b = np.zeros(n_points)
        b[indexes[starting_node]] = -1
        b[indexes[final_node]] = 1


        m.remove(m.getConstrs())
        m.addConstr(A@f==b)

        m.optimize()

        try:
            flows = m.getAttr("X", m.getVars())
        except:
            with open(f'./computation_results/initial_paths/err-{query}.txt', 'a+') as file:
                file.write(f'ERR: {tract} {poi_name} -- No solution found,\n')
            continue

        objval = m.ObjVal
        
        unrestricted_path_lengths[tract][poi_name]['length']=objval
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
            with open(f'./computation_results/initial_paths/err-{query}.txt', 'a+') as file:
                file.write(f'ERR {seg}: {tract} {poi_name} -- No path found,\n')
            continue

        unrestricted_path_lengths[tract][poi_name]['n_banned_nodes'] = len([pt for pt in pts if pt in red_nodes])
        
        json.dump(unrestricted_path_lengths, open(f'./computation_results/initial_paths/{query}-{seg}-{ts}.json', 'w'), indent=2)

        if not i: tqdm.tqdm.write(str(unrestricted_path_lengths))
        continue

        
