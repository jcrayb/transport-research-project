from main import socketio
from .utils import find_coords_from_address, find_coords_from_maps_url,\
                    to_caching_address,\
                    get_cached_coordinates, cache_coordinates,\
                    cache_places, get_cached_places

from time import sleep
from flask import Blueprint, render_template
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.actions.wheel_input import ScrollOrigin


places = Blueprint('places', __name__, url_prefix="/places",
                  template_folder="./templates", 
                  static_folder="./static", 
                  static_url_path="/static-places")

@socketio.on('places')
def test(data):
    address = data['address']
    query = data['query']

    print(address, query)

    places = get_cached_places(address=address)

    if places:
        socketio.emit('places-return', data=data_temp)
        return places

    coordinates = get_cached_coordinates(address=address)
    
    if not coordinates:
        coordinates = find_coords_from_address(address=address, sleep_timer=4, max_attempts=4)
        print(coordinates)
        cache_coordinates(address=address, coords=coordinates)

    if not coordinates:
        socketio.emit('places-return', data={'error':'Could not find address'})
        return
    
    zoom_level = 15

    times_scrolled = 5
    scroll_amount = 1000

    url = f'https://www.google.com/maps/search/{query}/@{coordinates[0]},{coordinates[1]},{zoom_level}z'

    with webdriver.Chrome() as browser:
        browser.set_window_size(1024, 768)
        browser.get(url)

        data_total = {}

        scroll_origin = ScrollOrigin.from_viewport(150, 200)

        for i in range(times_scrolled):
            ActionChains(browser)\
                .scroll_from_origin(scroll_origin, 0, scroll_amount)\
                .perform()
            sleep(2)
            #browser.execute_script("window.scrollBy(200,3000)","")

            soup = BeautifulSoup(browser.page_source, 'html.parser')

            results_div = soup.find('div', {'aria-label': f'Results for {query}'})

            
            divs = {div.find('div').find('a').attrs['aria-label']: div.find('div').find('a').attrs['href'] for div in results_div.find_all('div') if str(div)[:5] == '<div>' and div.find('div').find('a')}
            whole_divs = [div for div in results_div.find_all('div') if str(div)[:5] == '<div>' and div.find('div').find('a')]


            data_temp = {}

            for name, href in divs.items():
                coords = find_coords_from_maps_url(href)

                if name not in data_total:
                    data_temp[name] = coords
                    data_total[name] = coords
                
                
            socketio.emit('places-return', data=data_temp)
    cache_places(address=address, data=data_total)
    return data
    

@places.route('/')
def landing():
    return render_template('main.html')