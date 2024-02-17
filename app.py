import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import altair as alt
import folium
from streamlit_folium import st_folium
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Database connection string for SQLAlchemy
db_user = os.getenv('DB_USER')
db_pw = os.getenv('DB_PASSWORD')
db_host = os.getenv('DB_HOST')
db_port = os.getenv('DB_PORT')
db_name = os.getenv('DB_NAME')
sqlalchemy_conn_str = f'postgresql+psycopg2://{db_user}:{db_pw}@{db_host}:{db_port}/{db_name}'

# Create SQLAlchemy engine
engine = create_engine(sqlalchemy_conn_str)

# Set up the title of the dashboard
st.title("Seattle Events")

# Load data from the database
df = pd.read_sql_query("SELECT * FROM events", con=engine)

# Ensure the 'date' column is in datetime format and timezone-aware
df['date'] = pd.to_datetime(df['date'])  # Convert to datetime format
df['date'] = df['date'].dt.tz_convert('UTC')  # Correct way to convert existing timezone-aware datetimes to UTC

# Filter out rows with NaT values in the 'date' column
df = df.dropna(subset=['date'])

# Extract month and day of the week from the 'date' column
df['month'] = df['date'].dt.month_name()
df['day_of_week'] = df['date'].dt.day_name()

# Sidebar controls for filtering
category = st.sidebar.selectbox("Select a category", ['All'] + sorted(df['category'].unique().tolist()))
if category != 'All':
    df = df[df['category'] == category]

# Define a function to handle NaT values when parsing date input
def date_input_with_nat(label, value):
    try:
        return st.sidebar.date_input(label, value=value)
    except ValueError:
        return st.sidebar.date_input(label)

start_date = date_input_with_nat(
    "Select start date",
    value=df['date'].min()
)

end_date = date_input_with_nat(
    "Select end date",
    value=df['date'].max()
)

start_date = pd.to_datetime(start_date).tz_localize(None).tz_localize('UTC')
end_date = pd.to_datetime(end_date).tz_localize(None).tz_localize('UTC')

df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]

location = st.sidebar.selectbox("Select a location", ['All'] + sorted(df['location'].unique().tolist()))
if location != 'All':
    df = df[df['location'] == location]

# Initialize and display the map with event locations
m = folium.Map(location=[47.6062, -122.3321], zoom_start=12)
for _, row in df.iterrows():
    if pd.notnull(row['longitude']) and pd.notnull(row['latitude']):
        folium.Marker([row['latitude'], row['longitude']], popup=row['title']).add_to(m)
st_folium(m, width=800, height=400)

# Chart for Event Categories
chart_category = alt.Chart(df).mark_bar().encode(
    x=alt.X('count()', title='Number of Events'),
    y=alt.Y('category', sort='-x', title='Category'),
    tooltip=['category', 'count()']
).properties(title='Number of Events by Category').interactive()
st.altair_chart(chart_category, use_container_width=True)

# Chart for Month with Most Events
chart_month = alt.Chart(df).mark_bar().encode(
    x=alt.X('month:O', title='Month'),
    y=alt.Y('count()', title='Number of Events'),
    tooltip=['month', 'count()']
).properties(title='Number of Events by Month').interactive()
st.altair_chart(chart_month, use_container_width=True)

# Chart for Day of the Week with Most Events
chart_day_of_week = alt.Chart(df).mark_bar().encode(
    x=alt.X('day_of_week:O', sort='-x', title='Day of the Week'),
    y=alt.Y('count()', title='Number of Events'),
    tooltip=['day_of_week', 'count()']
).properties(title='Events by Day of the Week').interactive()
st.altair_chart(chart_day_of_week, use_container_width=True)

# Display filtered data as a table if the checkbox is checked
if st.checkbox('Show filtered data'):
    st.write(df)
