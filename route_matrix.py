"""Traffic-aware travel times from one origin to many destinations (Routes API computeRouteMatrix).

Billing (checked 2026-10-29, https://developers.google.com/maps/billing-and-pricing/sku-details):
  - Billed per ELEMENT (origins x destinations), not per request.
  - TRAFFIC_AWARE / TRAFFIC_AWARE_OPTIMAL -> "Compute Route Matrix Pro": 5,000 free elements/month.
  - TRAFFIC_UNAWARE                       -> "Compute Route Matrix Essentials": 10,000 free elements/month.
"""
from datetime import datetime, timezone
import argparse
import json
import os

import requests

URL = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
FIELD_MASK = "originIndex,destinationIndex,status,condition,duration,staticDuration,distanceMeters"
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


def compute_travel_times(origin, destinations, departure_time, api_key,
                         routing_preference="TRAFFIC_AWARE_OPTIMAL", traffic_model="BEST_GUESS"):
    """origin: (lat, lon); destinations: list of (lat, lon); departure_time: datetime (must not be in the past).

    traffic_model (BEST_GUESS, PESSIMISTIC, OPTIMISTIC) only applies with TRAFFIC_AWARE_OPTIMAL.
    Returns a list aligned with `destinations`: dicts with duration_s (with traffic),
    static_duration_s (without traffic) and distance_m, or None if no route was found.
    """
    if departure_time.tzinfo is not None and departure_time < datetime.now(timezone.utc):
        raise ValueError("departure_time is in the past; the Routes API rejects past departures for DRIVE")

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": FIELD_MASK,
    }
    chunk_size = MAX_ELEMENTS[routing_preference]
    results = [None] * len(destinations)

    for start in range(0, len(destinations), chunk_size):
        chunk = destinations[start:start + chunk_size]
        body = {
            "origins": [waypoint(*origin)],
            "destinations": [waypoint(*d) for d in chunk],
            "travelMode": "DRIVE",
            "routingPreference": routing_preference
        }
        if routing_preference == "TRAFFIC_AWARE_OPTIMAL":
            body["trafficModel"] = traffic_model

        if not routing_preference == "TRAFFIC_UNAWARE":
            body["departureTime"] = to_rfc3339(departure_time)

        response = requests.post(URL, headers=headers, json=body, timeout=60)
        if not response.ok:
            raise RuntimeError(f"Routes API error {response.status_code}: {response.text}")

        for element in response.json():
            # status is an empty object on success; condition is ROUTE_EXISTS or ROUTE_NOT_FOUND
            if element.get("status", {}).get("code") or element.get("condition") != "ROUTE_EXISTS":
                continue
            results[start + element["destinationIndex"]] = {
                "duration_s": int(element["duration"].rstrip("s")),
                "static_duration_s": int(element.get("staticDuration", "0s").rstrip("s")),
                "distance_m": element.get("distanceMeters", 0),
            }
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--origin", required=True, help="lat,lon")
    parser.add_argument("--dest", required=True, action="append", help="lat,lon (repeatable)")
    parser.add_argument("--departure", required=True,
                        help="ISO 8601 with offset, e.g. 2026-11-03T08:00:00-06:00")
    parser.add_argument("--routing", default="TRAFFIC_AWARE_OPTIMAL", choices=list(MAX_ELEMENTS))
    parser.add_argument("--traffic-model", default="BEST_GUESS", choices=["BEST_GUESS", "PESSIMISTIC", "OPTIMISTIC"])
    args = parser.parse_args()

    origin = tuple(float(x) for x in args.origin.split(","))
    destinations = [tuple(float(x) for x in d.split(",")) for d in args.dest]
    departure = datetime.fromisoformat(args.departure)

    times = compute_travel_times(origin, destinations, departure, load_api_key(),
                                 args.routing, args.traffic_model)
    print(json.dumps(dict(zip(args.dest, times)), indent=2))
