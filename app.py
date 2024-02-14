import streamlit as st
import pandas as pd
import pandas.io.sql as sqlio
import altair as alt
import json
from db import conn_str

# Title of the dashboard
st.title("Seattle Events Dashboard")

# Load data from the database
df = sqlio.read_sql_query("SELECT * FROM events", conn_str)
df['date'] = pd.to_datetime(df['date'], utc=True)
df['geolocation'] = df['geolocation'].apply(json.loads)
df['weather'] = df['weather'].apply(lambda x: json.loads(x) if pd.notnull(x) else {})

# Extracting month and day of the week
df['month'] = df['date'].dt.month_name()
df['day_of_week'] = df['date'].dt.day_name()

# Sidebar Controls
category = st.sidebar.selectbox("Select a Category", ['All'] + sorted(df['category'].unique()))
if category != 'All':
    df = df[df['category'] == category]

start_date, end_date = st.sidebar.date_input("Select Date Range", [df['date'].min(), df['date'].max()])
df = df[(df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))]

location = st.sidebar.selectbox("Select a Location", ['All'] + sorted(df['location'].unique()))
if location != 'All':
    df = df[df['location'] == location]

weather_condition = st.sidebar.selectbox("Filter by Weather Condition", ['All'] + sorted(df['weather'].apply(lambda x: x.get('condition', 'N/A')).unique()))
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

# 4. Where Events are Often Held
st.subheader("Event Locations")
location_chart = alt.Chart(df).mark_circle(size=60).encode(
    longitude='geolocation.longitude:Q',
    latitude='geolocation.latitude:Q',
    size='count():Q',
    color='location:N',
    tooltip=['venue', 'location', 'count()']
).properties(height=400)
st.altair_chart(location_chart, use_container_width=True)

# Optional: Display filtered data as a table
if st.checkbox('Show Filtered Data'):
    st.write(df)

