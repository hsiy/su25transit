# import pandas as pd
# from flask import Flask, render_template, request, jsonify
# import folium
# import os
# from datetime import datetime, timedelta, time
# import sqlite3

# # Path to the SQLite database
# base_path = os.path.dirname(__file__)
# db_path = os.path.join(base_path, 'transit_data.db')

# # Helper to load a table from the SQLite database
# def load_table(table_name):
#     with sqlite3.connect(db_path) as conn:
#         return pd.read_sql_query(f'SELECT * FROM {table_name}', conn)

# stop_times = load_table('stop_times')
# trips = load_table('trips')
# calendar = load_table('calendar')
# routes = load_table('routes')
# stops = load_table('stops')

# def expand_calendar(row):
#     days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
#     start_date = datetime.strptime(str(row['start_date']), '%Y%m%d')
#     end_date = datetime.strptime(str(row['end_date']), '%Y%m%d')
#     dates = []
#     current = start_date
#     while current <= end_date:
#         if row[days[current.weekday()]] == 1:
#             dates.append(current.strftime('%Y-%m-%d'))
#         current += timedelta(days=1)
#     return dates

# calendar['service_dates'] = calendar.apply(expand_calendar, axis=1)
# calendar_expanded = calendar.explode('service_dates').rename(columns={'service_dates': 'service_date'}).reset_index(drop=True)

# # Merge GTFS tables globally
# trips_routes = trips.merge(routes, on='route_id', how='left')
# merged = stop_times.merge(trips_routes[['trip_id', 'service_id', 'route_long_name']], on='trip_id', how='left')
# final = merged.merge(calendar_expanded, on='service_id', how='left')
# final = final.merge(stops[['stop_id', 'stop_name', 'stop_lat', 'stop_lon']], on='stop_id', how='left')

# # Parse datetime columns once globally
# final['arrival_datetime'] = pd.to_datetime(final['service_date'] + ' ' + final['arrival_time'], errors='coerce')
# final['departure_datetime'] = pd.to_datetime(final['service_date'] + ' ' + final['departure_time'], errors='coerce')

# app = Flask(__name__)

# @app.after_request
# def add_header(response):
#     response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, public, max-age=0"    
#     response.headers["Pragma"] = "no-cache"
#     response.headers["Expires"] = "0"
#     return response


# def forecast(stop_id, route_name, return_only=False):
#     df_specific = final[(final['stop_id'] == stop_id) & (final['route_long_name'] == route_name)].copy()
#     df_specific = df_specific.dropna(subset=['arrival_datetime'])
    
#     if df_specific.empty:
#         raise ValueError(f"No data found for stop_id={stop_id} and route_name='{route_name}'.")

#     now = datetime.now()
#     current_time = now.time()
    
#     # Define perimeters for capacity status
#     capacity_status = ''
#     if (datetime.strptime("06:30", "%H:%M").time() <= current_time <= datetime.strptime("08:00", "%H:%M").time()) \
#         or (datetime.strptime("16:00", "%H:%M").time() <= current_time <= datetime.strptime("18:00", "%H:%M").time()):
#         capacity_status = "<span style='color:orange;'>Full Standing Only</span>"
    
#     if (datetime.strptime("07:00", "%H:%M").time() <= current_time <= datetime.strptime("07:30", "%H:%M").time()) \
#         or (datetime.strptime("17:00", "%H:%M").time() <= current_time <= datetime.strptime("17:30", "%H:%M").time()):
#         # Peak within peak → max capacity
#         capacity_status = "<span style='color:red;'>At Max Capacity</span>"
    
#     # Compute next arrival as before
#     df_today = df_specific[df_specific['service_date'] == now.strftime('%Y-%m-%d')]
#     df_today['time_only'] = df_today['arrival_datetime'].dt.time
#     df_upcoming = df_today[df_today['time_only'] > current_time]
    
#     if not df_upcoming.empty:
#         next_arrival = df_upcoming.sort_values(by='arrival_datetime').iloc[0]['arrival_datetime']
#     else:
#         next_arrival = datetime.combine(now.date() + timedelta(days=1), datetime.strptime("05:00", "%H:%M").time())

#     next_arrival_str = next_arrival.strftime('%Y-%m-%d %I:%M:%S %p')

#     if return_only:
#         return next_arrival_str, capacity_status
#     else:
#         print(f"Next bus: {next_arrival_str}, Capacity: {capacity_status}")

# @app.route('/')
# def index():
#     bus_status = get_bus_capacity_status("route_long_name")
#     return render_template('index.html', bus_status=bus_status)

# @app.route('/map', methods=['GET', 'POST'])
# def map_view():
#     try:
#         latitude = float(request.form.get('latitude') or request.args.get('latitude'))
#         longitude = float(request.form.get('longitude') or request.args.get('longitude'))
#         selected_route_name = request.form.get('route_name') or request.args.get('route_name')
#         show_favorites_only = request.form.get('show_favorites_only') or request.args.get('show_favorites_only')
#         favorite_routes_list = [r for r in (request.form.get('favorite_routes') or request.args.get('favorite_routes') or '').split(',') if r]
#         favorite_stops_list = [s for s in (request.form.get('favorite_stops') or request.args.get('favorite_stops') or '').split(',') if s]

#         m = folium.Map(location=[latitude, longitude], zoom_start=13)
#         folium.Marker([latitude, longitude], popup='You are here').add_to(m)

#         stops_df = load_table('stops')
#         routes_df = load_table('routes')
#         stop_times_df = load_table('stop_times')
#         trips_df = load_table('trips')
#         try:
#             shapes_df = load_table('shapes')
#         except Exception:
#             shapes_df = pd.DataFrame()

#         trips_routes = trips_df.merge(routes_df, on='route_id', how='left')
#         if show_favorites_only:
#             if favorite_routes_list:
#                 trips_routes = trips_routes[trips_routes['route_long_name'].isin(favorite_routes_list)]
#             if favorite_stops_list:
#                 stops_df = stops_df[stops_df['stop_id'].astype(str).isin(favorite_stops_list)]
#         elif selected_route_name:
#             trips_routes = trips_routes[trips_routes['route_long_name'] == selected_route_name]

#         colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'lightred', 'beige', 'darkblue', 'darkgreen']

#         for idx, route_id in enumerate(trips_routes['route_id'].unique()):
#             route_info = routes_df[routes_df['route_id'] == route_id].iloc[0]
#             route_name = route_info['route_long_name']
#             route_color = f"#{route_info['route_color']}" if pd.notna(route_info.get('route_color')) else colors[idx % len(colors)]

#             for shape_id in trips_routes[trips_routes['route_id'] == route_id]['shape_id'].dropna().unique():
#                 shape_points = shapes_df[shapes_df['shape_id'] == shape_id].sort_values('shape_pt_sequence')
#                 if len(shape_points) >= 2:
#                     coords = shape_points[['shape_pt_lat', 'shape_pt_lon']].values.tolist()
#                     folium.PolyLine(coords, color=route_color, weight=4, opacity=0.8, popup=f"Route {route_name}").add_to(m)

#             stop_ids_for_route = stop_times_df[stop_times_df['trip_id'].isin(trips_df[trips_df['route_id'] == route_id]['trip_id'])]['stop_id'].unique()

#             for _, stop in stops_df[stops_df['stop_id'].isin(stop_ids_for_route)].iterrows():
#                 popup_html = f"""
#                 <div style='display:flex;align-items:center;gap:8px;'>
#                   <span class='stop-star' data-stopid='{stop['stop_id']}' data-stopname='{stop['stop_name']}' style='cursor:pointer;font-size:22px;color:#888;' title='Add to favorites'>&#9734;</span>
#                   <b>{stop['stop_name']}</b>
#                 </div>
#                 ID: {stop['stop_id']}<br>
#                 <a href="#" onclick="
#                     fetch('/forecast_api?stop_id={stop['stop_id']}&route_name={route_name}')
#                         .then(res => res.json())
#                         .then(data => {{
#                             if (data.error) {{
#                                 alert(data.error);
#                             }} else {{
#                                 var w = window.open('', 'popup', 'width=300,height=200');
#                                 w.document.write('<b>Route:</b> ' + data.route_name + '<br>');
#                                 w.document.write('<b>Stop ID:</b> ' + data.stop_id + '<br>');
#                                 w.document.write('<b>Next Arrival:</b> ' + data.next_arrival + '<br>');
#                                 w.document.write('<b>Bus Capacity:</b> ' + data.bus_capacity);
#                                 w.document.close();
#                             }}
#                         }});
#                     return false;">
#                 Get arrival time</a>
#                 """

#                 folium.CircleMarker(
#                     location=[stop['stop_lat'], stop['stop_lon']],
#                     radius=4,
#                     color=route_color,
#                     fillColor=route_color,
#                     fillOpacity=0.8,
#                     popup=folium.Popup(popup_html, max_width=250)
#                 ).add_to(m)

#         map_html = m._repr_html_()
#         routes_list = routes_df[['route_long_name']].drop_duplicates().to_dict('records')

#         average_capacity = get_average_bus_status()
#         # Example: check if a bus is full (replace with your real logic)
#         is_full_capacity = True  # <-- change this to your actual check
#         upcoming_capacity = get_upcoming_capacity(is_full_capacity)

#         return render_template(
#             "map_display_v2.html",
#             map_html=map_html,
#             routes=routes,
#             average_capacity=average_capacity,
#             upcoming_capacity=upcoming_capacity
#         )

#     except Exception as e:
#         print(f"Error loading GTFS data: {e}")
#         return f"Error loading GTFS data: {e}", 500

# @app.route('/forecast_api')
# def forecast_api():
#     stop_id = request.args.get('stop_id', type=int)
#     route_name = request.args.get('route_name', type=str)
    
#     if stop_id is None or not route_name:
#         return jsonify({'error': 'Missing stop_id or route_name'}), 400
    
#     try:
#         next_time, _ = forecast(stop_id, route_name, return_only=True)
#         capacity_status = get_bus_capacity_status(route_name)
#         return jsonify({
#             'stop_id': stop_id,
#             'route_name': route_name,
#             'next_arrival': next_time,
#             'bus_capacity': capacity_status
#         })
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500
    
# def get_bus_capacity_status(route_name):
#     now = datetime.now().time()
#     morning_start = time(6, 30)
#     morning_end = time(8, 0)
#     evening_start = time(16, 0)
#     evening_end = time(18, 0)
#     popular_routes = ["72nd / Ames Avenue", "ORBT", "24th Street", "Maple Street", "Center Street"]

#     if route_name in popular_routes:
#         return '<span style="color: red;">At Max Capacity</span>'

#     if morning_start <= now <= morning_end or evening_start <= now <= evening_end:
#         return '<span style="color: orange;">Full Standing Only</span>'
#     else:
#         return '<span style="color: green;">Open Seats</span>'
    
# def get_average_bus_status():
#     now = datetime.now().time()
#     morning_start = time(6, 30)
#     morning_end = time(8, 0)
#     evening_start = time(16, 0)
#     evening_end = time(18, 0)

#     if (morning_start <= now <= morning_end) or (evening_start <= now <= evening_end):
#         return '<span style="color:red;">Limited Space</span>'
#     else:
#         return '<span style="color:green;">Available spaces</span>'

# def get_upcoming_capacity(is_full_capacity):
#     if is_full_capacity:
#         return '<span style="color:orange;">Full Standing Only</span>'
#     return None

# if __name__ == '__main__':
#     app.run(debug=True)