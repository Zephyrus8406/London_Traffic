import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv
from shapely.geometry import LineString

load_dotenv()

TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY_2")
MIN_CONFIDENCE = 0.5
BASE_URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData"


def get_flow_segment(latitude, longitude, zoom=18, api_key=TOMTOM_API_KEY):
    if not api_key:
        raise RuntimeError("TOMTOM_API_KEY is missing. Check your .env file.")

    url = f"{BASE_URL}/absolute/{zoom}/json"
    params = {
        "key": api_key,
        "point": f"{latitude},{longitude}",
        "unit": "kmph",
        "openLr": "true",
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 403:
            print("Error 403: Invalid API key or regional restriction (check VPN/key).")
            return None
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"TomTom API request failed: {e}")
        return None


def parse_flow_response(data):
    if not data or "flowSegmentData" not in data:
        raise ValueError("Response does not contain flowSegmentData")

    flow = data["flowSegmentData"]
    coordinates = flow.get("coordinates", {}).get("coordinate", [])
    coords = [(p["longitude"], p["latitude"]) for p in coordinates]
    geometry = LineString(coords) if len(coords) >= 2 else None

    return {
        "current_speed": flow.get("currentSpeed"),
        "free_flow_speed": flow.get("freeFlowSpeed"),
        "current_travel_time": flow.get("currentTravelTime"),
        "free_flow_travel_time": flow.get("freeFlowTravelTime"),
        "confidence": flow.get("confidence"),
        "road_closure": flow.get("roadClosure", False),
        "frc": flow.get("frc"),
        "openlr": flow.get("openlr"),
        "geometry": geometry,
    }


def classify_traffic(record):
    if record.get("road_closure") is True:
        return "closed"

    current = record.get("current_speed")
    free_flow = record.get("free_flow_speed")
    confidence = record.get("confidence")

    if current is None or free_flow is None or confidence is None:
        return "missing"
    if confidence < MIN_CONFIDENCE:
        return "unreliable"
    if current <= 0 or free_flow <= 0:
        return "invalid_speed"

    return "valid"


def calculate_traffic_ratio(current_speed, free_flow_speed):
    if current_speed <= 0 or free_flow_speed <= 0:
        raise ValueError("Speeds must be positive")
    return current_speed / free_flow_speed


def calculate_travel_time(length_m, speed_kmh):
    if length_m < 0:
        raise ValueError("Length cannot be negative")
    if speed_kmh <= 0:
        raise ValueError("Speed must be positive")
    return 3.6 * length_m / speed_kmh


def process_traffic_record(record, length_m):
    status = classify_traffic(record)
    result = {
        "traffic_status": status,
        "is_closed": status == "closed",
        "traffic_ratio": None,
        "traffic_color": "missing",
        "traffic_time_s": None,
        "free_flow_time_s": None,
    }

    if status != "valid":
        return result

    current = record["current_speed"]
    free_flow = record["free_flow_speed"]
    ratio = calculate_traffic_ratio(current, free_flow)

    if ratio < 0.5:
        color = "red"
    elif ratio < 0.8:
        color = "yellow"
    else:
        color = "none"

    result.update({
        "traffic_ratio": ratio,
        "traffic_color": color,
        "traffic_time_s": calculate_travel_time(length_m, current),
        "free_flow_time_s": calculate_travel_time(length_m, free_flow),
    })
    return result


def save_matches(matches, filepath):
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    saved_matches = [
        {"edge": [u, v, key], "traffic": record}
        for (u, v, key), record in matches.items()
    ]
    snapshot = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "matches": saved_matches,
    }

    with filepath.open("w", encoding="utf-8") as file:
        json.dump(snapshot, file, indent=4)
    print(f"Saved {len(matches)} traffic matches to {filepath}.")


def load_matches(filepath):
    filepath = Path(filepath)
    with filepath.open("r", encoding="utf-8") as file:
        snapshot = json.load(file)

    matches = {}
    for item in snapshot["matches"]:
        u, v, key = map(int, item["edge"])
        matches[(u, v, key)] = item["traffic"]
    return matches


if __name__ == "__main__":
    # تست ۱: دریافت و تجزیه داده زنده برای یک نقطه در لندن
    raw_data = get_flow_segment(latitude=51.5215, longitude=-0.1300)
    if raw_data:
        traffic_record = parse_flow_response(raw_data)
        print("Live Parsed Record:", traffic_record)

    # تست ۲: محاسبه زمان سفر
    print("Sample Travel Time (s):", calculate_travel_time(length_m=200, speed_kmh=40))

    # تست ۳: پردازش یک رکورد فرضی
    sample_record = {
        "current_speed": 20,
        "free_flow_speed": 40,
        "confidence": 0.9,
        "road_closure": False,
    }
    print("Processed Record:", process_traffic_record(sample_record, length_m=150))