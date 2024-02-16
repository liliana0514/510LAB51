import streamlit as st
import pandas.io.sql as sqlio
import altair as alt
import folium
from streamlit_folium import st_folium
import pandas as pd
from db import conn_str

# Set up the title of the dashboard
st.title("Seattle Events")

# Load data from the database
df = sqlio.read_sql_query("SELECT * FROM events", conn_str)

# Ensure the 'date' column is in datetime format and timezone-aware
df['date'] = pd.to_datetime(df['date'], utc=True)

# Extract 'month' and 'day_of_week' from 'date'
df['month'] = df['date'].dt.month_name()
df['day_of_week'] = df['date'].dt.day_name()

# Sidebar controls for filtering
# Dropdown to filter by category
category = st.sidebar.selectbox("Select a category", ['All'] + list(df['category'].unique()))
if category != 'All':
    df = df[df['category'] == category]

# Date range selector for event date
start_date, end_date = st.sidebar.date_input("Select date range", [df['date'].min(), df['date'].max()])
# Ensure start_date and end_date are timezone-aware to match the 'date' column in the dataframe
start_date = pd.to_datetime(start_date).tz_localize('UTC')
end_date = pd.to_datetime(end_date).tz_localize('UTC')
df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]

# Filter by location
location = st.sidebar.selectbox("Select a location", ['All'] + list(df['location'].unique()))
if location != 'All':
    df = df[df['location'] == location]

# Display the map with dynamic event locations (Optional: customize this to add dynamic markers)
m = folium.Map(location=[47.6062, -122.3321], zoom_start=12)
folium.Marker([47.6062, -122.3321], popup='Seattle').add_to(m)
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
    x=alt.X('month', sort='-y', title='Month'),
    y=alt.Y('count()', title='Number of Events'),
    tooltip=['month', 'count()']
).properties(
    title='Events per Month'
).interactive()

st.altair_chart(chart_month, use_container_width=True)

# Chart for Day of the Week with Most Events
chart_day_of_week = alt.Chart(df).mark_bar().encode(
    x=alt.X('day_of_week', sort='-y', title='Day of the Week'),
    y=alt.Y('count()', title='Number of Events'),
    tooltip=['day_of_week', 'count()']
).properties(
    title='Events by Day of the Week'
).interactive()

st.altair_chart(chart_day_of_week, use_container_width=True)

# Optional: Display filtered data as a table if checkbox is checked
if st.checkbox('Show filtered data'):
    st.write(df)

