import pandas as pd
from flask import Flask, render_template, request
import folium
import os

app = Flask(__name__)

# Serves as the homepage with a map where users can select their location
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/map', methods=['POST'])
def map_view():
    print("POST /map received")
    print("Form data:", request.form)

    # Get latitude and longitude from the user input
    latitude = float(request.form['latitude'])
    longitude = float(request.form['longitude'])

    # Create a Folium map centered on the user's location
    m = folium.Map(location=[latitude, longitude], zoom_start=13)
    folium.Marker([latitude, longitude], popup='You are here').add_to(m)

    try:
        # Load all GTFS files
        stops_path = os.path.join(os.path.dirname(__file__), 'stops.csv')
        routes_path = os.path.join(os.path.dirname(__file__), 'routes.csv')
        stop_times_path = os.path.join(os.path.dirname(__file__), 'stop_times.csv')
        
        print(f"Loading GTFS data...")
        
        stops_df = pd.read_csv(stops_path)
        routes_df = pd.read_csv(routes_path)
        stop_times_df = pd.read_csv(stop_times_path)
        
        print(f"Stops: {stops_df.shape}, Routes: {routes_df.shape}, Stop times: {stop_times_df.shape}")
        
        # Show all stops in Omaha (remove distance filter)
        nearby_stops = stops_df
        
        # Add stops to map
        for _, stop in nearby_stops.iterrows():
            folium.CircleMarker(
                location=[stop['stop_lat'], stop['stop_lon']],
                radius=4,
                color='blue',
                fillColor='lightblue',
                fillOpacity=0.8,
                popup=f"{stop['stop_name']}<br>ID: {stop['stop_id']}"
            ).add_to(m)
        
        # Load trips.csv to connect trip_id to route_id
        trips_path = os.path.join(os.path.dirname(__file__), 'trips.csv')
        if os.path.exists(trips_path):
            trips_df = pd.read_csv(trips_path)
            print(f"Trips: {trips_df.shape}")
            
            # Load shapes.csv for actual route paths
            shapes_path = os.path.join(os.path.dirname(__file__), 'shapes.csv')
            if os.path.exists(shapes_path):
                shapes_df = pd.read_csv(shapes_path)
                print(f"Shapes: {shapes_df.shape}")
                
                # Define colors array
                colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'lightred', 'beige', 'darkblue', 'darkgreen']
                
                # Get unique routes and their shape.Links trips to routes to shapes
                route_shapes = pd.merge(trips_df[['route_id', 'shape_id']].drop_duplicates(), 
                                       shapes_df, on='shape_id', how='inner')
                
                # Debug: Check which routes have shapes vs which don't
                all_route_ids = trips_df['route_id'].unique()
                routes_with_shapes = route_shapes['route_id'].unique()
                routes_without_shapes = set(all_route_ids) - set(routes_with_shapes)

                print(f"Total routes: {len(all_route_ids)}")
                print(f"Routes with shapes: {len(routes_with_shapes)}")
                print(f"Routes without shapes: {len(routes_without_shapes)}")
                if routes_without_shapes:
                    print(f"Missing shapes for routes: {list(routes_without_shapes)[:5]}...")

                route_count = 0
                for route_id in route_shapes['route_id'].unique():
                    route_data = route_shapes[route_shapes['route_id'] == route_id]
                    
                    for shape_id in route_data['shape_id'].unique():
                        shape_points = route_data[route_data['shape_id'] == shape_id].sort_values('shape_pt_sequence')
                        
                        if len(shape_points) >= 2:
                            coords = shape_points[['shape_pt_lat', 'shape_pt_lon']].values.tolist()
                            
                            route_info = routes_df[routes_df['route_id'] == route_id]
                            if len(route_info) > 0:
                                route_info = route_info.iloc[0]
                                route_name = route_info['route_short_name']
                                route_color = f"#{route_info['route_color']}"
                            else:
                                route_name = str(route_id)
                                route_color = colors[route_count % len(colors)]
                            
                            folium.PolyLine(
                                coords,
                                color=route_color,
                                weight=4,
                                opacity=0.8,
                                popup=f"Route {route_name}"
                            ).add_to(m)
                            
                            print(f"Added route {route_name} shape {shape_id} with {len(shape_points)} points")
                    
                    route_count += 1
            else:
                print("shapes.csv not found")
        else:
            print("trips.csv not found")

        print(f"Total routes drawn: {route_count}")
        
    except Exception as e:
        print(f"Error loading GTFS data: {e}")

    # Pass the map HTML content directly to template
    return render_template('map_display.html', map_html=m._repr_html_())

if __name__ == '__main__':
    app.run(debug=True)


