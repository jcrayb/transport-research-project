import osmnx as ox
import time

def node_from_address(network ,address: str)->int:
    lat, lon = find_coords_from_address(address=address)
    return ox.nearest_nodes(network, lon, lat)

from time import sleep
from selenium import webdriver
import json 
import os

'''req_folders = [
    './modules/places/cached',
    './modules/places/cached/coordinates',
    './modules/places/cached/places'
]

for folder in req_folders:
    if not os.path.exists(folder):
        os.mkdir(folder)'''

def find_coords_from_maps_url(url:str)->tuple:
    fsplit = url.replace('?entry=ttu', '').split('!3d')[1].split('!4d')
    return (float(fsplit[0]), float(fsplit[1].split('!16s')[0]))

'''def find_coords_from_maps_url_0(url:str)->tuple:
    fsplit = url.split('/@')[1].split(',')
    return (fsplit[0], fsplit[1])'''

def find_coords_from_address(address:str, sleep_timer:float=5,
                             max_attempts:int=3)->tuple:
    with webdriver.Chrome() as browser:
        browser.get(f"https://www.google.com/maps/place/{address.replace(' ', '+')}")
        coords = None
        for i in range(max_attempts):
            sleep(sleep_timer)
            url = browser.current_url
            try:
                coords = find_coords_from_maps_url(url=url)
                break
            except Exception as e:
                print(e)
                pass
        return coords
    return coords

def to_caching_address(address: str) -> str:
    return address.strip().lower().replace(' ', '_').replace(',', '')

def cache_coordinates(coords: tuple, address: str) -> bool:
    try:
        with open(f"./modules/places/cached/coordinates/{to_caching_address(address=address)}", 'w') as f:
            f.write(f'{coords[0]},{coords[1]}')
    except Exception as e:
        print('cache coords')
        print(e)
        return False
    return True

def get_cached_coordinates(address: str) -> tuple:
    try:
        with open(f"modules/places/cached/coordinates/{to_caching_address(address=address)}", 'r') as f:
            coords = f.read().split(',')
            print(f"cached {coords[0], coords[1]}")
    except Exception as e:
        print('get cached coords')
        print(e)
        return False
    
    return (coords[0], coords[1])

def cache_places(address: tuple, data: dict) -> bool:
    try:
        with open(f"modules/places/cached/places/{to_caching_address(address=address)}.json", 'w') as f:
            json.dump(data, f)
    except Exception as e:
        print('cache places')
        print(e)
        return False
    return True

def get_cached_places(address: str) -> dict:
    try:
        with open(f"modules/places/cached/places/{to_caching_address(address=address)}.json", 'r') as f:
            data = json.load(f)
            print(f"cached d{data}")
    except Exception as e:
        print('get cached places')
        print(e)
        return False
    
    return data

def get_route_from_edges(edges: list, starting_node: int, final_node: int) -> list:
    flowed_edges = edges.copy()

    current_edge = [edge for edge in flowed_edges if edge[0] == starting_node][0]

    route_edges = [current_edge]
    route_pts = [current_edge[0]]

    flowed_edges.remove(current_edge)

    while len(flowed_edges):
        for edge in flowed_edges:
            if current_edge[1] == edge[0]:
                route_edges += [edge]
                route_pts += [edge[0]]
                flowed_edges.remove(edge)
                current_edge = edge
                continue

    route_pts += [final_node]
    return route_pts, route_edges

'''def get_edges_for_real(edges: list, starting_node: int, final_node: int) -> list:
    flowed_edges = edges.copy()

    current_point = starting_node
    matching_edges = [edge for edge in flowed_edges if edge[0] == current_point]

    if len(matching_edges) == 1 and matching_edges[0][1] == final_node:
        return None, matching_edges

    for edge in matching_edges:
        flowed_edges.remove(edge)
        current_edge, all_edges = get_edges_for_real(flowed_edges, edge[1], final_node)

        if not current_edge:
            return None, all_edges + [edge]
        
    return'''

def get_edges_for_real(edges: list, starting_node: int, final_node: int) -> list:
    matching_edges = [edge for edge in edges if edge[0] == starting_node]

    if len(matching_edges) == 1 and matching_edges[0][1] == final_node:
        return matching_edges

    for matching_edge in matching_edges:
        all_edges = get_edges_for_real([edge for edge in edges if edge != matching_edge], matching_edge[1], final_node)
        
        return all_edges + [matching_edge]

def find_path(edges, starting_edge, reversed=False):
    flowed_edges = edges.copy()

    current_idx = int(reversed)
    search_idx = (1-int(reversed))%2

    current_edge = starting_edge

    route_edges = [current_edge]
    route_pts = [current_edge[current_idx]]

    flowed_edges.remove(current_edge)

    while len(flowed_edges):
        for edge in flowed_edges:
            if current_edge[search_idx] == edge[current_idx]:
                route_edges += [edge]
                route_pts += [edge[current_idx]]
                flowed_edges.remove(edge)
                current_edge = edge
                continue
    
    if reversed: route_edges.reverse()

    return route_edges, route_pts

def get_unique_path(edges, starting_node, final_node):
    final_edges = [x for x in edges if x[1] == final_node]
    starting_edges = [x for x in edges if x[0] == starting_node]

    for starting_edge in starting_edges:
        start = time.time()
        current = time.time()
        while current-start <= 2:
            current = time.time()
            positive_path, positive_pts = find_path(edges, starting_edge, reversed=False)

            for final_edge in final_edges:
                negative_path = find_path(edges, final_edge, reversed=True)

                if positive_path == negative_path:
                    break

    return positive_path, positive_pts

def get_edges_and_points(edges: list, starting_node: int, final_node: int) -> list:
    path = get_edges_for_real(edges, starting_node, final_node)
    path.reverse()
    pts = [edge[0] for edge in path] + [final_node]
    return path, pts