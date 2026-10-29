## Objective
Build a headless backend batch processing pipeline to resolve origin-destination addresses and compute predictive travel-time distributions using traffic-aware Routes API matrices. Implement Routes API `ComputeRouteMatrix` client with traffic-aware `departureTime` parameters (12AM, 9:00 AM destination arrival constraints, departure from destination at 12:00 PM, 5:00 PM).

## Tech Stack
Python 3.11+, Google Maps Platform REST APIs.

## Google Maps Platform Services & Endpoints
- Geocoding API → `/maps/api/geocode/json` → Resolve raw address strings into canonical Place IDs and temporary geographic coordinates.
- Routes API → `https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix` → Stream origin-destination durations with predictive departure timestamps.

## Architecture

Headless backend execution only. Batch workers read origin-destination pairs from internal storage, resolve missing coordinates via Geocoding API, and batch elements into `ComputeRouteMatrix` POST requests. API keys remain protected in backend secret managers with IP/API restrictions. For each origin coordinate, saves time to destination in json with similar structure to existing files such as the one in `/Users/jcrb/Documents/github/atle/results`, where JSON follows:
- origin
    - destination
        - travel time (morning, midday, evening, midnight)

## Constraints & Gotchas
- Client-Side REST Prohibition: Run all REST calls server-side. Never execute direct browser calls to Google Maps REST endpoints.
- Field Masking: Always include `X-Goog-FieldMask: originIndex,destinationIndex,status,duration,distanceMeters` on Routes API requests to minimize payload size and optimize processing costs.

## Key Documentation
- https://developers.google.com/maps/documentation/routes/compute-route-matrix
- https://developers.google.com/maps/documentation/geocoding/overview
- https://cloud.google.com/maps-platform/terms