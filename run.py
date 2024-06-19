import argparse
import subprocess
import os

parser = argparse.ArgumentParser()

parser.add_argument("-i", "--instances", help="Number of parallel instances")
parser.add_argument("-q", "--query", help="What to search for ")

query = str(parser.parse_args().query)
instances = int(parser.parse_args().instances)

required_paths = [
    './computation_results',
    './computation_results/initial_paths',
    './computation_results/budget_paths',
]

for path in required_paths:
    if not os.path.exists(path):
        os.mkdir(path)

try:
    cmd = f'python3 compute_places_of_interest.py -q {query}'

    subprocess.run(cmd, shell=True)
except KeyboardInterrupt:
    pass

try:
    cmd = ' & '.join([f'python3 compute.py -q {query} -ts {instances} -s {i}' for i in range(instances)])

    subprocess.run(cmd, shell=True)
except KeyboardInterrupt:
    pass



print(cmd)
