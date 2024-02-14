import streamlit as st
import pandas as pd
import pandas.io.sql as sqlio
import altair as alt
import json
from db import conn_str

# Set up the title of the dashboard
st.title("Seattle Events Dashboard")

# Load data from the database
df = sqlio.read_sql_query("SELECT * FROM events", conn_str)

# Convert date columns to datetime and ensure timezone awareness
df['date'] = pd.to_datetime(df['date'], utc=True)

# Safely load JSON data for geolocation and weather columns
df['geolocation'] = df['geolocation'].apply(lambda x: json.loads(x) if pd.notnull(x) else {})
df['weather'] = df['weather'].apply(lambda x: json.loads(x) if pd.notnull(x) else {})

# Extract month and day of week for further analysis
df['month'] = df['date'].dt.month_name()
df['day_of_week'] = df['date'].dt.day_name()

# Sidebar Controls for filtering
category = st.sidebar.selectbox("Select a Category", ['All'] + sorted(df['category'].unique()))
if category != 'All':
    df = df[df['category'] == category]

start_date, end_date = st.sidebar.date_input("Select Date Range", [df['date'].min(), df['date'].max()])
start_date_utc = pd.to_datetime(start_date).tz_localize('UTC')
end_date_utc = pd.to_datetime(end_date).tz_localize('UTC')
df = df[(df['date'] >= start_date_utc) & (df['date'] <= end_date_utc)]

location = st.sidebar.selectbox("Select a Location", ['All'] + sorted(df['location'].unique()))
if location != 'All':
    df = df[df['location'] == location]

weather_condition = st.sidebar.selectbox("Filter by Weather Condition", ['All'] + sorted(set([w.get('condition', 'N/A') for w in df['weather']])))
if weather_condition != 'All':
    df = df[df['weather'].apply(lambda x: x.get('condition', 'N/A')) == weather_condition]

# Charts
# 1. Most Common Event Categories
st.subheader("Most Common Event Categories")
category_chart = alt.Chart(df).mark_bar().encode(
    x='count():Q',
    y=alt.Y('category:N', sort='-x'),
    color='category:N',
    tooltip=['category', 'count()']
).properties(height=400)
st.altair_chart(category_chart, use_container_width=True)

# 2. Month with the Most Events
st.subheader("Month with the Most Events")
month_chart = alt.Chart(df).mark_bar().encode(
    x=alt.X('month:N', sort='-y'),
    y='count():Q',
    color='month:N',
    tooltip=['month', 'count()']
).properties(height=400)
st.altair_chart(month_chart, use_container_width=True)

# 3. Day of the Week with the Most Events
st.subheader("Day of the Week with the Most Events")
day_chart = alt.Chart(df).mark_bar().encode(
    x=alt.X('day_of_week:N', sort='-y'),
    y='count():Q',
    color='day_of_week:N',
    tooltip=['day_of_week', 'count()']
).properties(height=400)
st.altair_chart(day_chart, use_container_width=True)

# 4. Event Locations Visualization
st.subheader("Event Locations")
location_chart = alt.Chart(df).transform_calculate(
    latitude="datum.geolocation.latitude",
    longitude="datum.geolocation.longitude"
).mark_circle(size=60).encode(
    longitude='longitude:Q',
    latitude='latitude:Q',
    size=alt.Size('count()', title='Number of Events'),
    color='location:N',
    tooltip=['venue', 'location', 'count()']
).properties(height=400)
st.altair_chart(location_chart, use_container_width=True)

# Optional: Display filtered data as a table
if st.checkbox('Show Filtered Data'):
    st.write(df)
