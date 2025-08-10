import os
import pandas as pd
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
import folium

app = Flask(__name__)



# Serves as the homepage with a map where users can select their location
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/map', methods=['POST'])
def map_view():
    latitude = float(request.form['latitude'])
    longitude = float(request.form['longitude'])

    m = folium.Map(location=[latitude, longitude], zoom_start=13)
    folium.Marker([latitude, longitude], popup='You are here').add_to(m)

    # load GTFS CSVs (assumes files are next to the app or inside google_transit/)
    base_dir = os.path.join(os.path.dirname(__file__), '')
    stops_path = os.path.join(base_dir, 'stops.csv')
    routes_path = os.path.join(base_dir, 'routes.csv')
    stop_times_path = os.path.join(base_dir, 'stop_times.csv')
    trips_path = os.path.join(base_dir, 'trips.csv')

    # fallback to google_transit folder if needed
    gtfs_folder = os.path.join(os.path.dirname(__file__), 'google_transit')
    if not os.path.exists(stops_path) and os.path.exists(os.path.join(gtfs_folder, 'stops.csv')):
        stops_path = os.path.join(gtfs_folder, 'stops.csv')
        routes_path = os.path.join(gtfs_folder, 'routes.csv')
        stop_times_path = os.path.join(gtfs_folder, 'stop_times.csv')
        trips_path = os.path.join(gtfs_folder, 'trips.csv')

    # read (wrap in try so we can still show map if gtfs missing)
    try:
        stops_df = pd.read_csv(stops_path)
        routes_df = pd.read_csv(routes_path)
        stop_times_df = pd.read_csv(stop_times_path)
        trips_df = pd.read_csv(trips_path)
    except Exception as e:
        print("Error reading GTFS:", e)
        stops_df = pd.DataFrame()
        routes_df = pd.DataFrame()
        stop_times_df = pd.DataFrame()
        trips_df = pd.DataFrame()

    # build routes_by_stop mapping
    routes_by_stop = {}
    if not stop_times_df.empty and not trips_df.empty and not routes_df.empty:
        merged = stop_times_df.merge(trips_df[['trip_id', 'route_id']], on='trip_id', how='left')
        merged = merged.merge(routes_df[['route_id', 'route_short_name', 'route_long_name']], on='route_id', how='left')
        for _, row in merged[['stop_id', 'route_short_name', 'route_long_name']].drop_duplicates().iterrows():
            sid = row['stop_id']
            routes_by_stop.setdefault(sid, []).append({
                'route_short_name': row.get('route_short_name'),
                'route_long_name': row.get('route_long_name')
            })

    # Add stops to map with dynamic route links
    for _, stop in stops_df.iterrows() if not stops_df.empty else []:
        sid = stop['stop_id']
        sname = stop.get('stop_name', '')
        lat = stop['stop_lat']
        lon = stop['stop_lon']

        routes_for_stop = routes_by_stop.get(sid, [])
        if routes_for_stop:
            links_html = ""
            for i, r in enumerate(routes_for_stop):
                rlong = r.get('route_long_name') or ''
                rshort = r.get('route_short_name') or ''
                label = rshort if pd.notna(rshort) and rshort != '' else (rlong if pd.notna(rlong) else 'Route')
                # escape single quotes for JS string
                js_route = str(rlong).replace("'", "\\'") if rlong else str(label).replace("'", "\\'")
                links_html += f"<a href='javascript:void(0)' onclick=\"getForecastForRoute({sid}, '{js_route}', {i});\">{label}</a>"
                links_html += f"<div id='forecast_{sid}_{i}' style='margin-bottom:6px; font-size:0.9em;'></div>"
            popup_html = f"""
                <b>Stop:</b> {sname}<br>
                <b>ID:</b> {sid}<br><br>
                {links_html}
            """
            folium.Marker(
                [lat, lon],
                popup=folium.Popup(popup_html, max_width=300, parse_html=True)
            ).add_to(m)
        else:
            # fallback simple marker if no route info
            folium.CircleMarker(
                location=[lat, lon],
                radius=4,
                color='blue',
                fillColor='lightblue',
                fillOpacity=0.8,
                popup=f"{sname}<br>ID: {sid}"
            ).add_to(m)

    # (optional) keep your existing shapes/trip drawing code here...
    # ... your existing route/shape drawing logic can remain unchanged

    return render_template('map_display.html', map_html=m._repr_html_())


# --- Forecast API endpoint ---
@app.route('/forecast_api')
def forecast_api():
    stop_id = request.args.get('stop_id', type=int)
    route_name = request.args.get('route_name', type=str)
    if stop_id is None or not route_name:
        return jsonify({'error': 'Missing stop_id or route_name'}), 400

    try:
        # point to your GTFS folder if you keep GTFS under google_transit/
        gtfs_folder = os.path.join(os.path.dirname(__file__), 'google_transit')
        next_time = forecast(stop_id, route_name, return_only=True, gtfs_folder=gtfs_folder)
        if not next_time:
            return jsonify({'error': 'No forecast available for this stop/route'}), 404
        return jsonify({'stop_id': stop_id, 'route_name': route_name, 'next_arrival': next_time})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)


