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

def fetch_weather(latitude, longitude):
    """Fetch weather data for the given latitude and longitude from NWS."""
    gridpoint_url = f"https://api.weather.gov/points/{latitude},{longitude}"
    try:
        response = requests.get(gridpoint_url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()  # Check for HTTP request errors
        gridpoint_data = response.json()
        forecast_url = gridpoint_data['properties']['forecast']

        forecast_response = requests.get(forecast_url)
        forecast_response.raise_for_status()  # Check for HTTP request errors
        forecast_data = forecast_response.json()
        period = forecast_data['properties']['periods'][0]

        # Extract weather information
        weather_condition = period.get('shortForecast')
        temperature = period.get('temperature')
        temperature_unit = period.get('temperatureUnit')

        return {
            'weather_condition': weather_condition,
            'temperature': temperature,
            'temperature_unit': temperature_unit,
        }
    except requests.RequestException as e:
        logging.error(f"Error fetching weather data: {e}")
    except KeyError as e:
        logging.error(f"KeyError: {e} not found in weather data response.")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
    return None



def get_detail_page():
    links = json.load(open(URL_LIST_FILE, 'r'))
    total_links = len(links)  # Total number of events to process
    data = []
    
    for index, link in enumerate(links, start=1):
        try:
            logging.info(f"Processing link {index} of {total_links}: {link}")
            response = requests.get(link, timeout=10)
            response.raise_for_status()  # Check for HTTP request errors
            
            # Extract event details
            title_match = html.unescape(re.findall(r'<h1 class="page-title" itemprop="headline">(.+?)</h1>', response.text))
            datetime_venue_match = re.findall(r'<h4><span>.*?(\d{1,2}/\d{1,2}/\d{4})</span> \| <span>(.+?)</span></h4>', response.text)
            metas_match = re.findall(r'<a href=".+?" class="button big medium black category">(.+?)</a>', response.text)
            
            title = title_match[0] if title_match else "Unknown"
            date = datetime.datetime.strptime(datetime_venue_match[0][0], '%m/%d/%Y').replace(tzinfo=ZoneInfo('America/Los_Angeles')).isoformat() if datetime_venue_match else None
            venue = datetime_venue_match[0][1].strip() if datetime_venue_match else "Unknown"
            category = html.unescape(metas_match[0]) if metas_match else "Unknown"
            location = metas_match[1] if len(metas_match) > 1 else "Unknown"

            # Attempt to get geolocation
            longitude, latitude = get_geolocation(location)

            # Initialize a dictionary for this event
            event = {
                'url': link,
                'title': title,
                'date': date,
                'venue': venue,
                'category': category,
                'location': location,
                'longitude': longitude,
                'latitude': latitude,
                'weather_condition': None,
                'temperature': None,
                'temperature_unit': None,
            }

            # Fetch and add weather information
            if longitude is not None and latitude is not None:
                weather_info = fetch_weather(latitude, longitude)
                if weather_info:  # Merge weather info into event details
                    event.update({
                        'weather_condition': weather_info['weather_condition'],
                        'temperature': weather_info['temperature'],
                        'temperature_unit': weather_info['temperature_unit'],
                    })

            data.append(event)
            logging.info(f"Processed link successfully: {link} ({index}/{total_links})")
        except Exception as e:
            logging.error(f"Error processing link {link}: {e}")

        time.sleep(1)  # Sleep to be polite to the servers

    # Save collected data to file
    with open(URL_DETAIL_FILE, 'w') as f:
        json.dump(data, f, indent=4)
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
        latitude DOUBLE PRECISION,
        weather_condition TEXT,  -- 新增：天气状况（晴、阴、雨等）
        temperature DOUBLE PRECISION,  -- 新增：最低温度
        temperature_unit TEXT  -- 新增：体感温度
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
        INSERT INTO events (url, title, date, venue, category, location, longitude, latitude, weather_condition, temperature, temperature_unit)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (url) DO NOTHING;
        '''
        try:
            # Here, we're assuming that the URL is unique for each event. Adjust as necessary.
            cur.execute(insert_query, (
            row['title'],  # 注意这里，根据您之前的代码，这里应该是 row['title'] 而不是 row['url']，因为您没有提取 url 作为一个独立的字段
            row['title'], 
            row['date'], 
            row['venue'], 
            row['category'], 
            row['location'], 
            row.get('longitude'), 
            row.get('latitude'), 
            row['weather_condition'], 
            row['temperature'], 
            row['temperature_unit'], 
        ))
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