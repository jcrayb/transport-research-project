import os 
import sys

module_path = os.path.abspath(os.path.join('..'))
if module_path not in sys.path:
    sys.path.append(module_path)

import importlib
import utils.places_of_interest

importlib.reload(utils.places_of_interest)

import json
import tqdm
import argparse

parser = argparse.ArgumentParser()

parser.add_argument("-q", "--query", help="What to search for ")

query = str(parser.parse_args().query)

with open(f'./computation_results/err-{query}.txt', 'w+') as f:
    f.write('')

census_tract_centroids = json.load(open('./osmnx/data/tract-centroids.json', 'r'))

census_tract_centroids = {key: (coords[1], coords[0]) for key, coords in census_tract_centroids.items()}

results = json.load(open(f'./computation_results/{query}.json', 'r')) if os.path.exists(f'./computation_results/{query}.json') else {}

for i in tqdm.trange(len(census_tract_centroids)):
    tract = list(census_tract_centroids.keys())[i]
    coords = census_tract_centroids[tract]

    if tract in results: continue
    
    try:
        places = utils.places_of_interest.get_places_from_coordinates(coords, query, zoom_level=13, amount_of_data=3)
        results[tract] = places
    except Exception as e:
        with open(f'./computation_results/err-{query}.txt', 'a+') as f:
            f.write(tract + f': {e} , ')
        print(tract)

    json.dump(results, open(f'./computation_results/{query}.json', 'w'), indent=1)
