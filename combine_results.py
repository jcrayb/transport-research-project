import json
import argparse
import os

parser = argparse.ArgumentParser()
parser.add_argument("--pass", dest="pass_name", choices=["initial", "budget"], required=True)
parser.add_argument("--label", required=True, help="POI category, fixed name, or 'commutes'")
parser.add_argument("-ts", "--totalsplits", type=int, required=True)
args = parser.parse_args()


def merge(into, other):
    for key, value in other.items():
        if isinstance(value, dict) and isinstance(into.get(key), dict):
            merge(into[key], value)
        else:
            into[key] = value


pass_dir = f"results/paths/{args.pass_name}"
merged = {}
for seg in range(args.totalsplits):
    part = f"{pass_dir}/{args.label}-{seg}-{args.totalsplits}.json"
    if not os.path.exists(part):
        print(f"missing {part}")
        continue
    merge(merged, json.load(open(part)))

out_file = f"{pass_dir}/{args.label}.json"
json.dump(merged, open(out_file, "w"), indent=2)
print(f"wrote {out_file} ({len(merged)} tracts)")
