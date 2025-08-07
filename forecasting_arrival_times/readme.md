# **Forecasting Transit arrival times**
- Import and process data from Google Transit Feed Specification (GTFS) files.
  - stop_times.txt – exact arrival and departure times for each stop.
  - trips.txt – mapping between trips and routes.
  - calendar.txt – service schedules.
  - routes.txt – general route descriptions.
  - stops.txt – geolocation and names of stops.
- Parese the mergeed datasets from the Googe Drive historical transit data
- Focus on specific stop_id and route_paths_name even assigning a 1 for each arrival time
- Apply statistical forecasting models to predict upcoming bus arrival times
