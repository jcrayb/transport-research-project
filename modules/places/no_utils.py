## COMPUTATIONS
from time import sleep
import json 
import os

## WEBSCRAPING
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.actions.wheel_input import ScrollOrigin
from selenium.webdriver.common.by import By

req_folders = [
    './modules/places/cached',
    './modules/places/cached/coordinates',
    './modules/places/cached/places'
]

for folder in req_folders:
    if not os.path.exists(folder):
        os.mkdir(folder)

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
        with open(f"./modules/places/cached/coordinates/{to_caching_address(address=address)}", 'r') as f:
            coords = f.read().split(',')
            print(f"cached {coords[0], coords[1]}")
    except Exception as e:
        print('get cached coords')
        print(e)
        return False
    
    return (coords[0], coords[1])

def cache_places(address: tuple, data: dict) -> bool:
    try:
        with open(f"./modules/places/cached/places/{to_caching_address(address=address)}.json", 'w') as f:
            json.dump(data, f)
    except Exception as e:
        print('cache places')
        print(e)
        return False
    return True

def get_cached_places(address: str) -> dict:
    try:
        with open(f"./modules/places/cached/places/{to_caching_address(address=address)}.json", 'r') as f:
            data = json.load(f)
            print(f"cached d{data}")
    except Exception as e:
        print('get cached places')
        print(e)
        return False
    
    return data



