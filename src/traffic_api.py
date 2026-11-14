

import requests
import os
from dotenv import load_dotenv
from shapely import Point

load_dotenv()
TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY")

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
            return data
        elif response.status_code == 403:
            print("invalid url / api key .")
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
    
    
