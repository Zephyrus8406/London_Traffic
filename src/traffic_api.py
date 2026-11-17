

import requests
import os
from dotenv import load_dotenv
from shapely import Point
from shapely.geometry import LineString

load_dotenv()
TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY_2")



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





