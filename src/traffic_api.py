

import requests
import os
from dotenv import load_dotenv
from shapely import Point
from shapely.geometry import LineString
import json
from pathlib import Path
from datetime import datetime, timezone




load_dotenv()
TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY_2")
MIN_CONFIDENCE = 0.5



def fetch_tomtom_data(lat, lon, api_key=TOMTOM_API_KEY):
    
    if not api_key:
        raise ValueError("api isnt valid")

    url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/relative0/10/json"
    params = {'point': f"{lat},{lon}",'unit': 'KMPH','key': api_key}
    
    try:
        response = requests.get(url, params=params, timeout=5)
        print('requesting for the data ...')
        if response.status_code == 200:
            data = response.json().get('flowSegmentData', {})
            #print(f'data from fetch data : { data}')
            return data
        elif response.status_code == 403:
            print("invalid url / api key  we are in iran , fetch tomtom data.")
            return None
        else:
            return None
    except Exception as e:
        print(f"Request failed: {e}")
        return None
    


def parse_tomtom_data(data):
    return {
    'current_speed': data.get('currentSpeed'),      
    'free_flow_speed': data.get('freeFlowSpeed'),   
    'confidence': data.get('confidence', 0.0),       
    'road_closure': data.get('roadClosure', False), 
    'coordinates': data.get('coordinates', {}).get('coordinate', [])
    }
    
    




BASE_URL = (
    "https://api.tomtom.com/traffic/services/4/"
    "flowSegmentData"
)


def get_flow_segment(latitude,longitude,zoom=18, API_KEY = TOMTOM_API_KEY):
    if not API_KEY:
        raise RuntimeError("TOMTOM_API_KEY is missing. ""Check your .env file.")
    url = (f"{BASE_URL}/absolute/{zoom}/json")
    params = {"key": API_KEY,"point": f"{latitude},{longitude}","unit": "kmph","openLr": "true"}
    response = requests.get(url,params=params,timeout=20)
    response.raise_for_status()
    return response.json()



def parse_flow_response(data):
    flow = data.get("flowSegmentData")
    if not flow:
        raise ValueError("Response does not contain flowSegmentData")
    coordinates = flow.get("coordinates", {}).get("coordinate", [])
    coords = [(p["longitude"], p["latitude"]) for p in coordinates]
    geometry = None
    if len(coords) >= 2:
        geometry = LineString(coords)
    return {
        "current_speed": flow.get("currentSpeed"),
        "free_flow_speed": flow.get("freeFlowSpeed"),
        "current_travel_time": flow.get("currentTravelTime"),
        "free_flow_travel_time": flow.get("freeFlowTravelTime"),
        "confidence": flow.get("confidence"),
        "road_closure": flow.get("roadClosure"),
        "frc": flow.get("frc"),
        "openlr": flow.get("openlr"),
        "geometry": geometry
    }



def classify_traffic(record):
    current = record["current_speed"]
    free_flow = record["free_flow_speed"]
    confidence = record["confidence"]
    closure = record["road_closure"]
    if closure is True:
        return "closed"
    if (current is None or free_flow is None or confidence is None):
        return "missing"
    if confidence < MIN_CONFIDENCE:
        return "unreliable"
    if current <= 0 or free_flow <= 0:
        return "invalid_speed"
    return "valid"



def calculate_travel_time(length_m,speed_kmh):
    if speed_kmh <= 0:
        raise ValueError("Speed must be positive")
    return 3.6 * length_m / speed_kmh




def classify_traffic(record):
    current = record.get("current_speed")
    free_flow = record.get("free_flow_speed")
    confidence = record.get("confidence")
    closure = record.get("road_closure")
    
    if closure is True:
        return "closed"
    # Missing information.
    if (current is None or free_flow is None or confidence is None):
        return "missing"
    # Low confidence .
    if confidence < MIN_CONFIDENCE:
        return "unreliable"
    # Invalid speeds 
    if current <= 0 or free_flow <= 0:
        return "invalid_speed"
    return "valid"

def calculate_traffic_ratio(current_speed,free_flow_speed):
    if current_speed <= 0 or free_flow_speed <= 0:
        raise ValueError("Speeds must be positive")
    return current_speed / free_flow_speed



def calculate_travel_time(length_m,speed_kmh):
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
        "free_flow_time_s": None
    }

    if status != "valid":
        return result

    current = record["current_speed"]
    free_flow = record["free_flow_speed"]

    ratio = calculate_traffic_ratio(
        current,
        free_flow
    )

    result.update({
        "traffic_ratio": ratio,
        "traffic_time_s": calculate_travel_time(
            length_m,
            current
        ),
        "free_flow_time_s": calculate_travel_time(
            length_m,
            free_flow
        )
    })

    if ratio < 0.5:
        result["traffic_color"] = "red"

    elif ratio < 0.8:
        result["traffic_color"] = "yellow"

    else:
        result["traffic_color"] = "none"

    return result




def save_matches(matches, filepath):
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    saved_matches = []
    for (u, v, key), record in matches.items():
        saved_matches.append({"edge": [u, v, key],"traffic": record})
    snapshot = {"collected_at": datetime.now(timezone.utc).isoformat(),"matches": saved_matches}
    with filepath.open("w", encoding="utf-8") as file:
        json.dump(snapshot, file, indent=4)
    print(f"Saved {len(matches)} traffic matches.")


def load_matches(filepath):
    filepath = Path(filepath)
    with filepath.open("r", encoding="utf-8") as file:
        snapshot = json.load(file)
    matches = {}
    for item in snapshot["matches"]:
        u, v, key = item["edge"]
        
        u = int(u)
        v = int(v)
        key = int(key)
        matches[(u, v, key)] = item["traffic"]
    return matches





if __name__ == '__main__':
    #lets go through an example 
    raw_data = get_flow_segment(latitude=51.5215,longitude=-0.1300)
    traffic_record = parse_flow_response(raw_data)
    print(traffic_record)
    #another example for the travel time 
    length = 200
    speed = 40
    travel_time = calculate_travel_time(length,speed)
    print(travel_time)
    
    
    record = {
        "current_speed": 20,
        "free_flow_speed": 40,
        "confidence": 0.9,
        "road_closure": False
    }
    processed = process_traffic_record(
        record,
        length_m=150
    )
    print(f' this is processed{processed}')






