# TECHIN 510 - Lab 5 
Seattle Events App

## Overview
Hi! This is the repository for my Seattle Events App for TECHIN 510.   

## How to Run

Create a gitignore as your first step! Put the following In your gitignore file! 
```
.env
venv
data
__pycache__
```

Put the following in your requirements.txt file
```
psycopg2-binary
requests
python-dotenv
streamlit-folium
sqlalchemy
```

Open the terminal and run the following commands:
```    
pip install -r requirements.txt 
pip install streamlit

```

Run the app using the command in the terminal
```bash
streamlit run app.py
```
## Detailed Comment for Every Part
- Function to fetch geolocation using Nominatim API
- Function to get detailed page information
- Function to insert data into PostgreSQL
- Database connection setup

## Lessons Learned
- Example visualization: Number of events by category
- Function to insert data into PostgreSQL

## Questions / Uncertainties
- If I want to scrape websites related to color analysis or color trends, how can I know which public webpages allow scrapeling? And how can I check if there is an official API provided?

## Contact

- Liliana Hsu
# TECHIN510






