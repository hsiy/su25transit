import pandas as pd
from flask import Flask, render_template, request, jsonify
import folium
import os
from datetime import datetime, timedelta
import sqlite3

# Path to the SQLite database
base_path = os.path.dirname(__file__)
db_path = os.path.join(base_path, 'transit_data.db')

# Helper to load a table from the SQLite database
def load_table(table_name):
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql_query(f'SELECT * FROM {table_name}', conn)

stop_times = load_table('stop_times')
trips = load_table('trips')
calendar = load_table('calendar')
routes = load_table('routes')
stops = load_table('stops')

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

calendar['service_dates'] = calendar.apply(expand_calendar, axis=1)
calendar_expanded = calendar.explode('service_dates').reset_index(drop=True)
calendar_expanded = calendar_expanded.rename(columns={'service_dates': 'service_date'})

# Merge trips and routes once globally
trips_routes = trips.merge(routes, on='route_id', how='left')
# Merge stop_times with trips_routes
merged = stop_times.merge(trips_routes[['trip_id', 'service_id', 'route_long_name']], on='trip_id', how='left')
# Merge with calendar_expanded
final = merged.merge(calendar_expanded, on='service_id', how='left')
# Merge with stops info
final = final.merge(stops[['stop_id', 'stop_name', 'stop_lat', 'stop_lon']], on='stop_id', how='left')

# Parse datetime columns once globally
final['arrival_datetime'] = pd.to_datetime(final['service_date'] + ' ' + final['arrival_time'], errors='coerce')
final['departure_datetime'] = pd.to_datetime(final['service_date'] + ' ' + final['departure_time'], errors='coerce')

app = Flask(__name__)

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, public, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

def forecast(stop_id, route_name, return_only=False):
    # Use the globally prepared 'final' DataFrame directly (no reloading or merging here)
    df_specific = final[(final['stop_id'] == stop_id) & (final['route_long_name'] == route_name)].copy()
    df_specific = df_specific.dropna(subset=['arrival_datetime'])

    if df_specific.empty:
        raise ValueError(f"No data found for stop_id={stop_id} and route_name='{route_name}'. "
                         f"Available route names: {final['route_long_name'].unique()}, stop_ids: {final['stop_id'].unique()}")

    df_specific['hour'] = df_specific['arrival_datetime'].dt.hour
    df_specific['minute'] = df_specific['arrival_datetime'].dt.minute

    minute_counts = df_specific.groupby(['hour', 'minute']).size().reset_index(name='count')
    minute_counts['probability'] = minute_counts.groupby('hour')['count'].transform(lambda x: x / x.sum())

    now = datetime.now()
    current_time = now.time()
    today_str = now.strftime('%Y-%m-%d')

    df_today = df_specific[df_specific['service_date'] == today_str].copy()
    df_today['time_only'] = df_today['arrival_datetime'].dt.time
    df_upcoming = df_today[df_today['time_only'] > current_time]

    if now.hour >= 23 or now.hour < 5:
        next_arrival = datetime.combine(now.date() + timedelta(days=1 if now.hour >= 23 else 0), datetime.strptime("05:00", "%H:%M").time())
    elif not df_upcoming.empty:
        next_arrival = df_upcoming.sort_values(by='arrival_datetime').iloc[0]['arrival_datetime']
    else:
        next_arrival = datetime.combine(now.date() + timedelta(days=1), datetime.strptime("05:00", "%H:%M").time())

    next_arrival_str = next_arrival.strftime('%Y-%m-%d %I:%M:%S %p')

    if return_only:
        return next_arrival_str
    else:
        print(f"Next bus is estimated to arrive at: {next_arrival_str}")
        
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/map', methods=['POST', 'GET'])
def map_view():
    print(f"{request.method} /map received")
    print("Form data:", request.form)

    latitude = float(request.form.get('latitude') or request.args.get('latitude'))
    longitude = float(request.form.get('longitude') or request.args.get('longitude'))
    selected_route_name = request.form.get('route_name') or request.args.get('route_name')
    show_favorites_only = request.form.get('show_favorites_only') or request.args.get('show_favorites_only')
    favorite_routes = request.form.get('favorite_routes') or request.args.get('favorite_routes')
    favorite_routes_list = [r for r in (favorite_routes or '').split(',') if r]

    m = folium.Map(location=[latitude, longitude], zoom_start=13)
    folium.Marker([latitude, longitude], popup='You are here').add_to(m)

    try:
        # Load from database instead of CSV
        stops_df = load_table('stops')
        routes_df = load_table('routes')
        stop_times_df = load_table('stop_times')
        trips_df = load_table('trips')
        # shapes may not always exist, so handle gracefully
        try:
            shapes_df = load_table('shapes')
        except Exception:
            shapes_df = pd.DataFrame()

        trips_routes = trips_df.merge(routes_df, on='route_id', how='left')

        all_routes = routes_df[['route_long_name']].drop_duplicates().rename(columns={'route_long_name': 'route_long_name'})
        routes = all_routes.to_dict('records')
        
        colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred',
                  'lightred', 'beige', 'darkblue', 'darkgreen']

        # Filter for favorites if toggled
        if show_favorites_only and favorite_routes_list:
            trips_routes = trips_routes[trips_routes['route_long_name'].isin(favorite_routes_list)]
        elif selected_route_name:
            trips_routes = trips_routes[trips_routes['route_long_name'] == selected_route_name]

        route_count = 0
        for route_id in trips_routes['route_id'].unique():
            route_info = routes_df[routes_df['route_id'] == route_id].iloc[0]
            route_name = route_info['route_long_name']
            route_color = f"#{route_info['route_color']}" if pd.notna(route_info.get('route_color')) else colors[route_count % len(colors)]

            shapes_for_route = trips_routes[trips_routes['route_id'] == route_id]['shape_id'].dropna().unique()
            for shape_id in shapes_for_route:
                shape_points = shapes_df[shapes_df['shape_id'] == shape_id].sort_values('shape_pt_sequence')
                if len(shape_points) >= 2:
                    coords = shape_points[['shape_pt_lat', 'shape_pt_lon']].values.tolist()
                    folium.PolyLine(coords, color=route_color, weight=4, opacity=0.8,
                                    popup=f"Route {route_name}").add_to(m)

            stop_ids_for_route = stop_times_df[stop_times_df['trip_id'].isin(
                trips_df[trips_df['route_id'] == route_id]['trip_id']
            )]['stop_id'].unique()

            for _, stop in stops_df[stops_df['stop_id'].isin(stop_ids_for_route)].iterrows():
                # Use route_name in popup link params
                popup_html = f"""
                <b>{stop['stop_name']}</b><br>
                ID: {stop['stop_id']}<br>
                <a href="#" onclick="
                    fetch('/forecast_api?stop_id={stop['stop_id']}&route_name={route_name}')
                        .then(res => res.json())
                        .then(data => {{
                            if (data.error) {{
                                alert(data.error);
                            }} else {{
                                var w = window.open('', 'popup', 'width=300,height=200');
                                w.document.write('<h2>Arrival Info</h2>');
                                w.document.write('<b>Route:</b> ' + data.route_name + '<br>');
                                w.document.write('<b>Stop ID:</b> ' + data.stop_id + '<br>');
                                w.document.write('<b>Next Arrival:</b> ' + data.next_arrival);
                                w.document.close();
                            }}
                        }});
                    return false;
                ">
                Get arrival time</a>
                """

                folium.CircleMarker(
                    location=[stop['stop_lat'], stop['stop_lon']],
                    radius=4,
                    color=route_color,
                    fillColor=route_color,
                    fillOpacity=0.8,
                    popup=folium.Popup(popup_html, max_width=250)
                ).add_to(m)

            route_count += 1

        map_html = m._repr_html_()

        return render_template(
            'map_display.html',
            map_html=map_html,
            routes=routes,
            selected_route_name=selected_route_name,
            request=request
        )

    except Exception as e:
        print(f"Error loading GTFS data: {e}")
        return f"Error loading GTFS data: {e}", 500

@app.route('/forecast_api')
def forecast_api():
    stop_id = request.args.get('stop_id', type=int)
    route_name = request.args.get('route_name', type=str)
    if stop_id is None or not route_name:
        return jsonify({'error': 'Missing stop_id or route_name'}), 400

    try:
        next_time = forecast(stop_id, route_name, return_only=True)
        if not next_time:
            return jsonify({'error': 'No forecast available for this stop/route'}), 404
        return jsonify({
            'stop_id': stop_id,
            'route_name': route_name,
            'next_arrival': next_time
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)