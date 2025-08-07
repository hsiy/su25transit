"""
Filename: Forecasting_next_trip
Last Written: Yefry (8/6/25)
Description:
    This code reads and collects all data contained in stop_times.txt, trips.txt, calendar.txt, routes.txt, stops.txt
    from google drive zip file of historical transit times.
    Looks at specific stop_id and places a 1 for arrival times
    Finds the probability of arrival time for each hour/minute.
    Using Darts model to find amount of arrivals per hour and statistically forecasting arrival times

Libraries:
    - pandas
    - datetime
    -matplotlib
    - statsmodel
Notes:
    - If any problems arise reach out to
        *Yefry
    -Website of the historical transit travels located in
        *website: https://drive.google.com/uc?export=download&id=1CtljMG4EgKsOF9yiSKpPDrMuZyGa1ykY
    - Further understanding of dataset see TransitLand.com
    Outputs next days time of arrival time
"""

import pandas as pd
from datetime import datetime, timedelta, date
import matplotlib.pyplot as plt

#function that collects the stop_id and route chosen.
def forecast(stop_id, route_name):
    # GFTS file
    stop_times = pd.read_csv(r'C:\Users\yepas\PycharmProjects\pythonProject\Intro SE\google_transit\stop_times.txt')
    trips = pd.read_csv(r'C:\Users\yepas\PycharmProjects\pythonProject\Intro SE\google_transit\trips.txt')
    calendar = pd.read_csv(r'C:\Users\yepas\PycharmProjects\pythonProject\Intro SE\google_transit\calendar.txt')
    routes = pd.read_csv(r'C:\Users\yepas\PycharmProjects\pythonProject\Intro SE\google_transit\routes.txt')
    stops = pd.read_csv(r'C:\Users\yepas\PycharmProjects\pythonProject\Intro SE\google_transit\stops.txt')
    # create calendar with actual dates
    def expand_calendar(row):
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        start_date = datetime.strptime(str(row['start_date']), '%Y%m%d')
        end_date = datetime.strptime(str(row['end_date']), '%Y%m%d')

        dates = []
        current = start_date
        while current <= end_date:
            if row[days[current.weekday()]] == 1:
                dates.append(current.strftime('%Y-%m-%d'))
            current += timedelta(days=1)
        return dates
    #Create calendar dates
    calendar['service_dates'] = calendar.apply(expand_calendar, axis=1)
    calendar_expanded = calendar.explode('service_dates').reset_index(drop=True)
    calendar_expanded = calendar_expanded.rename(columns={'service_dates': 'service_date'})

    # Merge txt data together
    trips = trips.merge(routes, on='route_id', how='left')
    merged = stop_times.merge(trips[['trip_id', 'service_id', 'route_short_name', 'route_long_name']], on='trip_id', how='left')
    final = merged.merge(calendar_expanded, on='service_id', how='left')
    final = final.merge(stops[['stop_id', 'stop_name', 'stop_lat', 'stop_lon']], on='stop_id', how='left')

    #Parse datetime
    final['arrival_datetime'] = pd.to_datetime(final['service_date'] + ' ' + final['arrival_time'], errors='coerce')
    final['departure_datetime'] = pd.to_datetime(final['service_date'] + ' ' + final['departure_time'], errors='coerce')

    # Stop_id and route_name
    stop_id_of_interest = stop_id
    route_long_name_of_interest = route_name

    df_specific = final[(final['stop_id'] == stop_id_of_interest) & (final['route_long_name'] == route_long_name_of_interest)].copy()
    df_specific = df_specific.dropna(subset=['arrival_datetime'])

    #checks if correct route and stop id is present
    if df_specific.empty:
        print(f"[ERROR] No data found for stop_id={stop_id_of_interest} and route_long_name='{route_long_name_of_interest}'")
        print("Available route_long_names:", final['route_long_name'].unique(), "And stop_id", final['stop_id'].unique())
        exit()


    # Extract hour and minute
    df_specific['hour'] = df_specific['arrival_datetime'].dt.hour
    df_specific['minute'] = df_specific['arrival_datetime'].dt.minute

    # Group to get historical pattern
    minute_counts = df_specific.groupby(['hour', 'minute']).size().reset_index(name='count')
    minute_counts['probability'] = minute_counts.groupby('hour')['count'].transform(lambda x: x / x.sum())

    if minute_counts.empty:
        print("[ERROR] No minute-wise arrival patterns found after grouping.")
        exit()

    #Forecasting next arrival time
    # Use most common hour/minute
    now = datetime.now()
    current_time = now.time()
    today_str = now.strftime('%Y-%m-%d')

    # Filter arrivals
    df_today = df_specific[df_specific['service_date'] == today_str].copy()
    df_today['time_only'] = df_today['arrival_datetime'].dt.time
    df_upcoming = df_today[df_today['time_only'] > current_time]

    # If it's after 11 PM or before 5 AM, show 5:00 AM arrival
    if now.hour >= 23 or now.hour < 5:
        next_arrival = datetime.combine(now.date() + timedelta(days=1 if now.hour >= 23 else 0), datetime.strptime("05:00", "%H:%M").time())
        print("It is currently outside regular service hours.")
        print(f"Next bus will arrive at: {next_arrival.strftime('%Y-%m-%d %I:%M:%S %p')}")
    elif not df_upcoming.empty:
        # Get next arrival time
        next_arrival = df_upcoming.sort_values(by='arrival_datetime').iloc[0]['arrival_datetime']
        print(f"Next bus is estimated to arrive at: {next_arrival.strftime('%Y-%m-%d %I:%M:%S %p')}")
    else:
        # No buses left today; return tomorrow at 5 AM
        next_arrival = datetime.combine(now.date() + timedelta(days=1), datetime.strptime("05:00", "%H:%M").time())
        print("No more buses today.")
        print(f"Next bus will arrive at: {next_arrival.strftime('%Y-%m-%d %I:%M:%S %p')}")

if __name__ == '__main__':
    forecast(9255, "72nd / Ames Avenue")
