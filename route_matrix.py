"""Traffic-aware travel times from one origin to many destinations (Routes API).

Two endpoints, selected with `endpoint`:
  - "matrix": computeRouteMatrix, one request per chunk of up to 625 (or 100) destinations.
  - "routes": computeRoutes, one request per destination.

Billing (checked 2026-11-06, https://developers.google.com/maps/billing-and-pricing/sku-details):
  - matrix is billed per ELEMENT (origins x destinations); routes is billed per REQUEST.
    With one origin, both come to one billable event per destination.
  - TRAFFIC_AWARE / TRAFFIC_AWARE_OPTIMAL -> "Pro" SKU: 5,000 free events/month.
  - TRAFFIC_UNAWARE                       -> "Essentials" SKU: 10,000 free events/month.
  - Compute Routes and Compute Route Matrix are separate SKUs, each with its own free cap.
"""
from datetime import datetime, timezone
import argparse
import json
import os

import requests

MATRIX_URL = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
MATRIX_FIELD_MASK = "originIndex,destinationIndex,status,condition,duration,staticDuration,distanceMeters"
ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
ROUTES_FIELD_MASK = "routes.duration,routes.staticDuration,routes.distanceMeters"
ENDPOINTS = ["matrix", "routes"]
# max elements per request: 625 normally, 100 with TRAFFIC_AWARE_OPTIMAL
MAX_ELEMENTS = {"TRAFFIC_UNAWARE": 625, "TRAFFIC_AWARE": 625, "TRAFFIC_AWARE_OPTIMAL": 100}


def load_api_key(path="key"):
    if os.environ.get("GOOGLE_MAPS_API_KEY"):
        return os.environ["GOOGLE_MAPS_API_KEY"]
    with open(path) as f:
        return f.read().strip()


def waypoint(lat, lon):
    return {"waypoint": {"location": {"latLng": {"latitude": lat, "longitude": lon}}}}


def to_rfc3339(departure_time):
    # naive datetimes are treated as UTC; pass a tz-aware datetime to use local time
    if departure_time.tzinfo is None:
        departure_time = departure_time.replace(tzinfo=timezone.utc)
    return departure_time.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def seconds(duration):
    # the API returns durations as strings like "1500s"
    return int(duration.rstrip("s"))


def route_options(departure_time, routing_preference, traffic_model):
    # request fields shared by both endpoints
    body = {"travelMode": "DRIVE", "routingPreference": routing_preference}
    if routing_preference == "TRAFFIC_AWARE_OPTIMAL":
        body["trafficModel"] = traffic_model
    if not routing_preference == "TRAFFIC_UNAWARE":
        body["departureTime"] = to_rfc3339(departure_time)
    return body


def post(url, field_mask, body, api_key):
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": field_mask,
    }
    response = requests.post(url, headers=headers, json=body, timeout=60)
    if not response.ok:
        raise RuntimeError(f"Routes API error {response.status_code}: {response.text}")
    return response.json()


def compute_travel_times(origin, destinations, departure_time, api_key,
                         routing_preference="TRAFFIC_AWARE_OPTIMAL", traffic_model="BEST_GUESS",
                         endpoint="matrix"):
    """origin: (lat, lon); destinations: list of (lat, lon); departure_time: datetime (must not be in the past).

    traffic_model (BEST_GUESS, PESSIMISTIC, OPTIMISTIC) only applies with TRAFFIC_AWARE_OPTIMAL.
    endpoint: "matrix" (computeRouteMatrix) or "routes" (computeRoutes, one request per destination).
    Returns a list aligned with `destinations`: dicts with duration_s (with traffic),
    static_duration_s (without traffic) and distance_m, or None if no route was found.
    """
    if departure_time.tzinfo is not None and departure_time < datetime.now(timezone.utc):
        raise ValueError("departure_time is in the past; the Routes API rejects past departures for DRIVE")

    options = route_options(departure_time, routing_preference, traffic_model)
    if endpoint == "matrix":
        return _compute_with_matrix(origin, destinations, options, api_key)
    if endpoint == "routes":
        return _compute_with_routes(origin, destinations, options, api_key)
    raise ValueError(f"endpoint must be one of {ENDPOINTS}, got {endpoint!r}")


def _compute_with_matrix(origin, destinations, options, api_key):
    chunk_size = MAX_ELEMENTS[options["routingPreference"]]
    results = [None] * len(destinations)

    for start in range(0, len(destinations), chunk_size):
        chunk = destinations[start:start + chunk_size]
        body = {
            "origins": [waypoint(*origin)],
            "destinations": [waypoint(*d) for d in chunk],
            **options,
        }
        for element in post(MATRIX_URL, MATRIX_FIELD_MASK, body, api_key):
            # status is an empty object on success; condition is ROUTE_EXISTS or ROUTE_NOT_FOUND
            if element.get("status", {}).get("code") or element.get("condition") != "ROUTE_EXISTS":
                continue
            results[start + element["destinationIndex"]] = {
                "duration_s": seconds(element["duration"]),
                "static_duration_s": seconds(element.get("staticDuration", "0s")),
                "distance_m": element.get("distanceMeters", 0),
            }
    return results


def _compute_with_routes(origin, destinations, options, api_key):
    results = []
    for destination in destinations:
        body = {
            # computeRoutes takes the Waypoint directly, without the RouteMatrix wrapper
            "origin": waypoint(*origin)["waypoint"],
            "destination": waypoint(*destination)["waypoint"],
            **options,
        }
        # the response is {} when no route exists
        routes = post(ROUTES_URL, ROUTES_FIELD_MASK, body, api_key).get("routes")
        if not routes:
            results.append(None)
            continue
        route = routes[0]
        results.append({
            "duration_s": seconds(route["duration"]),
            "static_duration_s": seconds(route.get("staticDuration", "0s")),
            "distance_m": route.get("distanceMeters", 0),
        })
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--origin", required=True, help="lat,lon")
    parser.add_argument("--dest", required=True, action="append", help="lat,lon (repeatable)")
    parser.add_argument("--departure", required=True,
                        help="ISO 8601 with offset, e.g. 2026-11-03T08:00:00-06:00")
    parser.add_argument("--routing", default="TRAFFIC_AWARE_OPTIMAL", choices=list(MAX_ELEMENTS))
    parser.add_argument("--endpoint", default="matrix", choices=ENDPOINTS,
                        help="matrix = computeRouteMatrix, routes = computeRoutes (one request per destination)")
    parser.add_argument("--traffic-model", default="BEST_GUESS", choices=["BEST_GUESS", "PESSIMISTIC", "OPTIMISTIC"])
    args = parser.parse_args()

    origin = tuple(float(x) for x in args.origin.split(","))
    destinations = [tuple(float(x) for x in d.split(",")) for d in args.dest]
    departure = datetime.fromisoformat(args.departure)

    times = compute_travel_times(origin, destinations, departure, load_api_key(),
                                 args.routing, args.traffic_model, args.endpoint)
    print(json.dumps(dict(zip(args.dest, times)), indent=2))
