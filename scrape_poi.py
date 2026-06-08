from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.actions.wheel_input import ScrollOrigin
from time import sleep
import json
import tqdm
import argparse
import os

parser = argparse.ArgumentParser()
parser.add_argument("-q", "--query", required=True, help="POI category to search for")
query = parser.parse_args().query


def find_coords_from_maps_url(url):
    fsplit = url.replace("?entry=ttu", "").split("!3d")[1].split("!4d")
    return (float(fsplit[0]), float(fsplit[1].split("!16s")[0]))


def get_places_from_coordinates(coordinates, query, zoom_level=15, amount_of_data=5):
    op = webdriver.ChromeOptions()
    op.add_argument("headless")
    url = f"https://www.google.com/maps/search/{query}/@{coordinates[0]},{coordinates[1]},{zoom_level}z"
    with webdriver.Chrome(options=op) as browser:
        browser.set_window_size(1024, 768)
        browser.get(url)

        scroll_origin = ScrollOrigin.from_viewport(150, 200)
        for i in range(amount_of_data):
            ActionChains(browser).scroll_from_origin(scroll_origin, 0, 1000).perform()
            sleep(2)

        soup = BeautifulSoup(browser.page_source, "html.parser")
        results_div = soup.find("div", {"aria-label": f"Results for {query}"})
        divs = {div.find("div").find("a").attrs["aria-label"]: div.find("div").find("a").attrs["href"]
                for div in results_div.find_all("div")
                if str(div)[:5] == "<div>" and div.find("div").find("a")}

    data = {}
    for name, href in divs.items():
        try:
            data[name] = find_coords_from_maps_url(href)
        except:
            continue
    return data


os.makedirs("results/poi", exist_ok=True)
out_file = f"results/poi/{query}.json"

centroids = json.load(open("data/tract-centroids.json"))
# centroids are stored [lon, lat]; the scraper wants (lat, lon)
centroids = {tract: (coords[1], coords[0]) for tract, coords in centroids.items()}

results = json.load(open(out_file)) if os.path.exists(out_file) else {}

for tract in tqdm.tqdm(centroids):
    if tract in results:
        continue
    try:
        results[tract] = get_places_from_coordinates(centroids[tract], query, zoom_level=13, amount_of_data=3)
    except Exception as e:
        print(tract, e)
    json.dump(results, open(out_file, "w"), indent=1)
