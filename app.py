import streamlit as st
import pandas.io.sql as sqlio
import altair as alt
import folium
from streamlit_folium import st_folium
import pandas as pd
import json
from db import conn_str
import pytz

# Set up the title of the dashboard
st.title("Seattle Events")

# Load data from the database
df = sqlio.read_sql_query("SELECT * FROM events", conn_str)

# Ensure the 'date' column is in datetime format and timezone-aware
df['date'] = pd.to_datetime(df['date'], utc=True)

# Sidebar controls for filtering
# Dropdown to filter by category
category = st.sidebar.selectbox("Select a category", ['All'] + list(df['category'].unique()))
if category != 'All':
    df = df[df['category'] == category]

# Date range selector for event date
start_date, end_date = st.sidebar.date_input(
    "Select date range",
    value=[df['date'].min(), df['date'].max()],
    min_value=df['date'].min(),
    max_value=df['date'].max()
)

# Convert start_date and end_date to timezone-aware datetime objects
# Note: 'tz_localize(None)' is used to remove any existing timezone information before applying 'tz_localize('UTC')'
start_date = pd.to_datetime(start_date).tz_localize(None).tz_localize('UTC')
end_date = pd.to_datetime(end_date).tz_localize(None).tz_localize('UTC')

# Apply filters to the dataframe
df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]

# Filter by location
location = st.sidebar.selectbox("Select a location", ['All'] + list(df['location'].unique()))
if location != 'All':
    df = df[df['location'] == location]

# Initialize the map
m = folium.Map(location=[47.6062, -122.3321], zoom_start=12)

# Display the map with dynamic event locations
for _, row in df.iterrows():
    # Ensure geolocation data is present and valid
    if pd.notnull(row['geolocation']):
        geolocation = json.loads(row['geolocation'])
        if geolocation['latitude'] and geolocation['longitude']:
            folium.Marker([geolocation['latitude'], geolocation['longitude']], popup=row['title']).add_to(m)

st_folium(m, width=800, height=400)

# Chart for Event Categories
chart_category = alt.Chart(df).mark_bar().encode(
    x=alt.X('count()', title='Number of Events'),
    y=alt.Y('category', sort='-x', title='Category'),
    tooltip=['category', 'count()']
).properties(
    title='Number of Events by Category'
).interactive()
st.altair_chart(chart_category, use_container_width=True)

# Chart for Month with Most Events
chart_month = alt.Chart(df).mark_bar().encode(
    x=alt.X('month:O', sort='-y', title='Month'),  # Explicitly specify data type as ordinal
    y=alt.Y('count()', title='Number of Events'),
    tooltip=['month:N', 'count()']  # Here, specifying month as nominal in tooltip is also fine
).properties(
    title='Events per Month'
).interactive()

# Chart for Day of the Week with Most Events
chart_day_of_week = alt.Chart(df).mark_bar().encode(
    x=alt.X('day_of_week:O', sort='-y', title='Day of the Week'),  # Explicitly specify data type as ordinal
    y=alt.Y('count()', title='Number of Events'),
    tooltip=['day_of_week:N', 'count()']  # Here, specifying day_of_week as nominal in tooltip is also fine
).properties(
    title='Events by Day of the Week'
).interactive()

# Optional: Display filtered data as a table if checkbox is checked
if st.checkbox('Show filtered data'):
    st.write(df)
