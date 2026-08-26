## Layout

```
solve.py            the unified solver (was the six c_*.py scripts)
scrape_poi.py       scrape nearest POIs around each tract from Google Maps
combine_results.py  merge the per-segment result files into one
data/               input data (centroids, camera nodes, commuting pairs, geo/, census/)
results/            generated outputs: poi/ scrapes, paths/{initial,budget}/, tables/ (CSV)
analysis/           analysis.ipynb (statsmodels) reads results/tables/, plus figures/
notebooks/          dev notebooks
```

## Setup

```bash
python -m venv ./
. ./bin/activate
pip install -r requirements.txt
```

The solver requires a Gurobi license valid for Gurobi 13.

## Pipeline

1. **Scrape points of interest** (OPTIONAL: only for the `poi` scope):

   ```bash
   python scrape_poi.py --query high-school   # -> results/poi/high-school.json
   ```

2. **Solve**. Each run computes the `initial` pass then the `budgets` pass.
   The tract list is split into `-ts` segments so runs can be parallelized;
   `-s` selects the 0-indexed segment.

   ```bash
   # fixed destination (e.g. O'Hare); the three hubs are three coordinate runs
   python solve.py --scope fixed --latitude 41.984025 --longitude -87.851528 -s 0 -ts 8

   # nearest POI of a category, per tract
   python solve.py --scope poi --option high-school -s 0 -ts 8

   # commuting origin->destination pairs
   python solve.py --scope commutes -s 0 -ts 8
   ```

   Add `--integer` for integer (rather than continuous) flow variables.
   Results land in `results/paths/{initial,budget}/{label}-{s}-{ts}.json`.

3. **Combine** the per-segment files into one:

   ```bash
   python combine_results.py --pass initial --label high-school -ts 8
   python combine_results.py --pass budget  --label high-school -ts 8
   ```

4. **Analyze** (reads `results/tables/`, writes `analysis/figures/`):

   Use `analysis/analysis.ipynb`
