import os
import re
import json
import datetime
from zoneinfo import ZoneInfo
import html
import requests
from bs4 import BeautifulSoup
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from db import get_db_conn

# Ensure the data directory exists
data_directory = './data'
if not os.path.exists(data_directory):
    os.makedirs(data_directory)

URL = 'https://visitseattle.org/events/page/'
URL_LIST_FILE = os.path.join(data_directory, 'links.json')
URL_DETAIL_FILE = os.path.join(data_directory, 'data.json')

# Initialize the geocoder with a user_agent
geolocator = Nominatim(user_agent="event_geocoder")
# Use RateLimiter to avoid hitting the service too frequently
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1, max_retries=2)

def list_links():
    res = requests.get(URL + '1/')
    last_page_no = int(re.findall(r'bpn-last-page-link"><a href=".+?/page/(\d+?)/.+" title="Navigate to last page">', res.text)[0])
    links = []
    for page_no in range(1, last_page_no + 1):
        res = requests.get(URL + str(page_no) + '/')
        if res.status_code == 200:
            links.extend(re.findall(r'<h3 class="event-title"><a href="(https://visitseattle.org/events/.+?/)" title=".+?">.+?</a></h3>', res.text))
        else:
            print(f"Failed to fetch page {page_no}: Status code {res.status_code}")
    json.dump(links, open(URL_LIST_FILE, 'w'))

def get_detail_page():
    links = json.load(open(URL_LIST_FILE, 'r'))
    data = []
    for link in links:
        try:
            res = requests.get(link)
            if res.status_code == 200:
                content = res.text
                row = {}
                row['title'] = html.unescape(re.findall(r'<h1 class="page-title" itemprop="headline">(.+?)</h1>', content)[0])
                datetime_venue = re.findall(r'<h4><span>.*?(\d{1,2}/\d{1,2}/\d{4})</span> \| <span>(.+?)</span></h4>', content)[0]
                row['date'] = datetime.datetime.strptime(datetime_venue[0], '%m/%d/%Y').replace(tzinfo=ZoneInfo('America/Los_Angeles')).isoformat()
                row['venue'] = datetime_venue[1].strip()
                metas = re.findall(r'<a href=".+?" class="button big medium black category">(.+?)</a>', content)
                row['category'] = html.unescape(metas[0])
                row['location'] = metas[1]
                row['url'] = link
                
                location = geocode(row['venue'])
                if location:
                    print(f"Successfully geocoded {row['venue']}")
                    row['latitude'] = location.latitude
                    row['longitude'] = location.longitude
                else:
                    print(f"Failed to geocode {row['venue']}")
                    row['latitude'], row['longitude'] = None, None
                
                data.append(row)
            else:
                print(f"Failed to fetch {link}: Status code {res.status_code}")
        except Exception as e:
            print(f'Error processing {link}: {e}')
    json.dump(data, open(URL_DETAIL_FILE, 'w'), indent=4)

def insert_to_pg():
    q = '''
    CREATE TABLE IF NOT EXISTS events (
        url TEXT PRIMARY KEY,
        title TEXT,
        date TIMESTAMP WITH TIME ZONE,
        venue TEXT,
        category TEXT,
        location TEXT,
        latitude NUMERIC,
        longitude NUMERIC
    );
    '''
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute(q)

    data = json.load(open(URL_DETAIL_FILE, 'r'))
    for row in data:
        try:
            q = '''
            INSERT INTO events (url, title, date, venue, category, location, latitude, longitude)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (url) DO NOTHING;
            '''
            cur.execute(q, (row['url'], row['title'], row['date'], row['venue'], row['category'], row['location'], row.get('latitude'), row.get('longitude')))
        except Exception as e:
            print(f"Database insertion error for {row['title']}: {e}")

if __name__ == '__main__':
    list_links()
    get_detail_page()
    insert_to_pg()
