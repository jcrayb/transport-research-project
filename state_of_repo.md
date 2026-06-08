## Nomenclature

`single` => Refers to a single destination, with user-defined coordinates, in this case the 3 transportation hubs

`poi` => Refers to local Points-Of-Interest, so for example the nearest high-school, hospital, etc. Can also average over $n$-nearest of a specific category

`weighted` => Refers to commuting paterns, so we work over each home/work pair. The weights are referring to the weights assigned from the city's dataset, which if I recall correctly account for household size & other factors

`initial` => Refers to un-constrained path, so pure shortest path

`budgets` => Refers to constrained path. Computed after the initial pass, from which we also derive the # of cameras on the way. This then tries again with the added constraint of only allowing the program to pass through a certain number of cameras.

## Utility files

`compute_places_of_interest.py` => Pre-computes a JSON file with the coordinates of nearest points of interest (high-school, hospital, etc.) around the center of a certain tract.

`compute_places_of_interest.py` => For each tract, compute the impact of ATLE for $n$-nearest POI. (basically exactly the same as `c_poi_budgets.py`?)

`main.py` => Contains (too) many utility functions. Some to scrape data from Google Maps, some pathfinding functions (why not use NetworkX?), some are wrappers around OSMNX functions to make them work with human-readable addresses.

## Analysis Utils

`graphs.ipynb` => Contains the graphs I used for the IISE conference.

`new-analysis.rmd` => Contains the R code used to get the p-values for the linear/quadratic models fitted.
