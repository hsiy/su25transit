Transit Code: Real-Time Bus Route Visualizer
This application is a simple Flask web app that allows users to input their location and view nearby bus routes and stops on an interactive map.
The map is generated using the Folium library and displays location-based transit information.
For the backend, we use statistical analysis of historical data to approximate the next arrival time, factoring in travel time.

Milestones
Milestone 1
Display the user’s current location as a marker.

Milestone 2
Draw bus routes from a bus_routes.csv file.

Show bus stops with green bus icons labeled with stop names.

Milestone 3
Read and process all data from stop_times.txt, trips.txt, calendar.txt, routes.txt, and stops.txt obtained from a Google Drive ZIP file of historical transit times.

Identify specific stop_id and route paths, assigning a 1 for each arrival time.

Calculate the probability of arrival times for each hour and minute.

Use the Darts time series forecasting library to:

Determine the number of arrivals per hour.

Statistically forecast upcoming arrival times.
