import re
import json
import datetime
from zoneinfo import ZoneInfo
import html
import requests
from db import get_db_conn

URL = 'https://visitseattle.org/events/page/'
URL_LIST_FILE = './data/links.json'
URL_DETAIL_FILE = './data/data.json'

def get_lat_lon(location):
    params = {'q': location, 'format': 'json'}
    response = requests.get('https://nominatim.openstreetmap.org/search', params=params)
    data = response.json()
    if data:
        return data[0]['lat'], data[0]['lon']
    return None, None

def get_weather(lat, lon):
    # Construct URL for National Weather Service API
    points_url = f"https://api.weather.gov/points/{lat},{lon}"
    try:
        points_response = requests.get(points_url)
        points_response.raise_for_status()
        grid_id, grid_x, grid_y = points_response.json()['properties']['gridId'], points_response.json()['properties']['gridX'], points_response.json()['properties']['gridY']

        # Fetching the detailed forecast
        forecast_url = f"https://api.weather.gov/gridpoints/{grid_id}/{grid_x},{grid_y}/forecast"
        forecast_response = requests.get(forecast_url)
        forecast_response.raise_for_status()
        
        # Extracting the detailed forecast information
        forecast_data = forecast_response.json()
        periods = forecast_data['properties']['periods']
        detailed_forecast = periods[0]['detailedForecast'] if periods else "No detailed forecast data"

        return detailed_forecast

    except requests.RequestException as e:
        return f"Weather data not available: {e}"

def list_links():
    res = requests.get(URL + '1/')
    last_page_no = int(re.findall(r'bpn-last-page-link"><a href=".+?/page/(\d+)/.+" title="Navigate to last page">', res.text)[0])
    links = []
    for page_no in range(1, last_page_no + 1):
        res = requests.get(URL + str(page_no) + '/')
        links.extend(re.findall(r'<h3 class="event-title"><a href="(https://visitseattle.org/events/.+?/)" title=".+?">.+?</a></h3>', res.text))
    json.dump(links, open(URL_LIST_FILE, 'w'))

def get_detail_page():
    links = json.load(open(URL_LIST_FILE, 'r'))
    data = []
    for link in links:
        row = {}
        try:
            res = requests.get(link)
            row['title'] = html.unescape(re.findall(r'<h1 class="page-title" itemprop="headline">(.+?)</h1>', res.text)[0])
            datetime_venue = re.findall(r'<h4><span>.*?(\d{1,2}/\d{1,2}/\d{4})</span> \| <span>(.+?)</span></h4>', res.text)[0]
            row['date'] = datetime.datetime.strptime(datetime_venue[0], '%m/%d/%Y').replace(tzinfo=ZoneInfo('America/Los_Angeles')).isoformat()
            row['venue'] = datetime_venue[1].strip()
            row['category'] = html.unescape(re.findall(r'<a href=".+?" class="button big medium black category">(.+?)</a>', res.text)[0])
            row['location'] = re.findall(r'<div class="location">(.+?)</div>', res.text)[0]

            # Fetch and print geolocation data
            lat, lon = get_lat_lon(row['venue'] + ', Seattle')
            print(f"Geolocation for {row['venue']}: {lat}, {lon}")  # Debug print

            # Fetch and print weather data
            weather = get_weather(lat, lon)
            print(f"Weather for {row['venue']}: {weather}")  # Debug print

            row['geolocation'] = json.dumps({'latitude': lat, 'longitude': lon})
            row['weather'] = json.dumps(weather)
            data.append(row)
        except Exception as e:
            print(f"Error processing link {link}: {e}")
    json.dump(data, open(URL_DETAIL_FILE, 'w'))

def insert_to_pg():
    q = '''
    CREATE TABLE IF NOT EXISTS events (
        url TEXT PRIMARY KEY,
        title TEXT,
        date TIMESTAMP WITH TIME ZONE,
        venue TEXT,
        category TEXT,
        location TEXT,
        geolocation JSONB,
        weather JSONB
    );
    '''
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute(q)
    
    urls = json.load(open(URL_LIST_FILE, 'r'))
    data = json.load(open(URL_DETAIL_FILE, 'r'))
    for row in data:
        q = '''
        INSERT INTO events (url, title, date, venue, category, location, geolocation, weather)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (url) DO NOTHING;
        '''
        # Ensure 'row['url']' is correctly defined and used here
        cur.execute(q, (row['url'], row['title'], row['date'], row['venue'], row['category'], row['location'], row['geolocation'], row['weather']))


if __name__ == '__main__':
    list_links()
    get_detail_page()
    insert_to_pg()