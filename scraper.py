import re
import json
import datetime
import logging
from zoneinfo import ZoneInfo
import html
import requests
from db import get_db_conn
from geopy.geocoders import Nominatim
import time

# 日誌設置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

URL = 'https://visitseattle.org/events/page/'
URL_LIST_FILE = './data/links.json'
URL_DETAIL_FILE = './data/data.json'

def list_links():
    try:
        res = requests.get(URL + '1/', timeout=10)
        last_page_no = int(re.findall(r'bpn-last-page-link"><a href=".+?/page/(\d+?)/.+" title="Navigate to last page">', res.text)[0])

        links = []
        for page_no in range(1, last_page_no + 1):
            logging.info(f"Fetching links from page {page_no} of {last_page_no}")
            res = requests.get(URL + str(page_no) + '/', timeout=10)
            links.extend(re.findall(r'<h3 class="event-title"><a href="(https://visitseattle.org/events/.+?/)" title=".+?">.+?</a></h3>', res.text))

        json.dump(links, open(URL_LIST_FILE, 'w'))
        logging.info("Links have been saved to file.")
    except Exception as e:
        logging.error(f"Error fetching links: {e}")


def get_geolocation(location):
    geolocator = Nominatim(user_agent="MySeattleEventsApp/1.0")
    try:
        geo_location = geolocator.geocode(location)
        if geo_location:
            return geo_location.longitude, geo_location.latitude
        else:
            return None, None
    except Exception as e:
        logging.error(f"Error getting geolocation for {location}: {e}")
        return None, None

def get_detail_page():
    links = json.load(open(URL_LIST_FILE, 'r'))
    total_links = len(links)  # Total number of events to process
    data = []
    for index, link in enumerate(links, start=1):
        try:
            logging.info(f"Processing link {index} of {total_links}: {link}")
            res = requests.get(link, timeout=10)
            row = {}
            row['title'] = html.unescape(re.findall(r'<h1 class="page-title" itemprop="headline">(.+?)</h1>', res.text)[0])
            datetime_venue = re.findall(r'<h4><span>.*?(\d{1,2}/\d{1,2}/\d{4})</span> \| <span>(.+?)</span></h4>', res.text)[0]
            row['date'] = datetime.datetime.strptime(datetime_venue[0], '%m/%d/%Y').replace(tzinfo=ZoneInfo('America/Los_Angeles')).isoformat()
            row['venue'] = datetime_venue[1].strip()
            metas = re.findall(r'<a href=".+?" class="button big medium black category">(.+?)</a>', res.text)
            if metas:
                row['category'] = html.unescape(metas[0])
                if len(metas) > 1:
                    row['location'] = metas[1]
                else:
                    row['location'] = "Unknown"
            else:
                row['category'] = "Unknown"
                row['location'] = "Unknown"

            # Attempt to get geolocation
            longitude, latitude = get_geolocation(row['location'])
            row['longitude'] = longitude
            row['latitude'] = latitude

            data.append(row)
            logging.info(f"Processed link successfully: {link} ({index}/{total_links})")
        except Exception as e:
            logging.error(f"Error processing link {link}: {e}")
        # Sleep to respect the policy of the geolocation service or website
        time.sleep(1)
    json.dump(data, open(URL_DETAIL_FILE, 'w'), indent=4)
    logging.info("Event details have been saved to file.")

def insert_to_pg():
    # SQL query to create the table with additional columns for longitude and latitude
    create_table_query = '''
    CREATE TABLE IF NOT EXISTS events (
        url TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        date TIMESTAMP WITH TIME ZONE NOT NULL,
        venue TEXT NOT NULL,
        category TEXT NOT NULL,
        location TEXT NOT NULL,
        longitude DOUBLE PRECISION,
        latitude DOUBLE PRECISION
    );
    '''
    
    # Establish database connection and create cursor
    conn = get_db_conn()
    cur = conn.cursor()
    
    # Execute the table creation query
    try:
        cur.execute(create_table_query)
        conn.commit()
    except Exception as e:
        logging.error(f"Error creating table: {e}")
        return
    
    # Load the URLs and detailed event data from the respective JSON files
    try:
        data = json.load(open('./data/data.json', 'r'))
    except Exception as e:
        logging.error(f"Error loading data from JSON: {e}")
        return
    
    # Iterate over each event's data
    for row in data:
        # SQL query to insert data into the table
        insert_query = '''
        INSERT INTO events (url, title, date, venue, category, location, longitude, latitude)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (url) DO NOTHING;
        '''
        try:
            # Here, we're assuming that the URL is unique for each event. Adjust as necessary.
            cur.execute(insert_query, (row['title'], row['title'], row['date'], row['venue'], row['category'], row['location'], row.get('longitude'), row.get('latitude')))
            conn.commit()
        except Exception as e:
            logging.error(f"Error inserting data for {row['title']}: {e}")
            # Optionally rollback if you want to maintain transaction integrity
            # conn.rollback()
    
    # Close the cursor and connection to clean up
    cur.close()
    conn.close()
    
    logging.info("Data insertion to PostgreSQL database is complete.")



if __name__ == '__main__':
    list_links()
    get_detail_page()
    insert_to_pg()
    logging.info("Scraper has finished running.")