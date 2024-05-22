## WEBSCRAPING
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.actions.wheel_input import ScrollOrigin
from selenium.webdriver.common.by import By

from time import sleep
from utils.main import find_coords_from_address, find_coords_from_maps_url

def get_places_from_address(address:str, query:str, zoom_level:int = 15, amount_of_data:int = 5) -> dict:
    coordinates = find_coords_from_address(address=address, sleep_timer=4, max_attempts=4)

    scroll_amount = 1000
    url = f'https://www.google.com/maps/search/{query}/@{coordinates[0]},{coordinates[1]},{zoom_level}z'
    with webdriver.Chrome() as browser:
        browser.set_window_size(1024, 768)
        browser.get(url)

        scroll_origin = ScrollOrigin.from_viewport(150, 200)

        for i in range(amount_of_data):
            ActionChains(browser)\
                .scroll_from_origin(scroll_origin, 0, scroll_amount)\
                .perform()
            sleep(2)
        #browser.execute_script("window.scrollBy(200,3000)","")

        soup = BeautifulSoup(browser.page_source, 'html.parser')

        results_div = soup.find('div', {'aria-label': f'Results for {query}'})
        
        divs = {div.find('div').find('a').attrs['aria-label']: div.find('div').find('a').attrs['href'] for div in results_div.find_all('div') if str(div)[:5] == '<div>' and div.find('div').find('a')}
        whole_divs = [div for div in results_div.find_all('div') if str(div)[:5] == '<div>' and div.find('div').find('a')]
        
        data = {}
        for name, href in divs.items():
            data[name] = find_coords_from_maps_url(href)
    return data

def get_places_from_coordinates(coordinates:tuple, query:str, zoom_level:int = 15, amount_of_data:int = 5) -> dict:
    scroll_amount = 1000
    url = f'https://www.google.com/maps/search/{query}/@{coordinates[0]},{coordinates[1]},{zoom_level}z'
    with webdriver.Chrome() as browser:
        browser.set_window_size(1024, 768)
        browser.get(url)

        scroll_origin = ScrollOrigin.from_viewport(150, 200)

        for i in range(amount_of_data):
            ActionChains(browser)\
                .scroll_from_origin(scroll_origin, 0, scroll_amount)\
                .perform()
            sleep(2)
        #browser.execute_script("window.scrollBy(200,3000)","")

        soup = BeautifulSoup(browser.page_source, 'html.parser')

        results_div = soup.find('div', {'aria-label': f'Results for {query}'})
        
        divs = {div.find('div').find('a').attrs['aria-label']: div.find('div').find('a').attrs['href'] for div in results_div.find_all('div') if str(div)[:5] == '<div>' and div.find('div').find('a')}
        whole_divs = [div for div in results_div.find_all('div') if str(div)[:5] == '<div>' and div.find('div').find('a')]
        
        data = {}
        for name, href in divs.items():
            try:
                data[name] = find_coords_from_maps_url(href)
            except:
                continue
    return data