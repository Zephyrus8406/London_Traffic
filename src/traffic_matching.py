from shapely.geometry import LineString
from traffic_api import fetch_tomtom_data , parse_tomtom_data
from load_graph import load_graph
from matching_graphs import *
from traffic_api import *


def get_edge_midpoint(u_data, v_data, edge_data):
    
    if 'geometry' in edge_data:
        geom = edge_data['geometry']
        midpoint = geom.interpolate(0.5, normalized=True)
        return midpoint.y, midpoint.x
    else:
        mid_lat = (u_data['y'] + v_data['y']) / 2.0
        mid_lon = (u_data['x'] + v_data['x']) / 2.0
        return mid_lat, mid_lon


def get_edge_midpoint_simplified_func(edge_geometry):
    midpoint = edge_geometry.interpolate(0.5,normalized=True)
    return midpoint.y, midpoint.x


def enrich_graph_with_traffic(G, max_queries=150):
    query_count = 0
    matched_edges = 0
    nodes , edges = ox.convert.graph_to_gdfs(G , nodes = True , edges = True )
    
    
    for u, v, k, data in G.edges(keys=True, data=True):
        u_node = G.nodes[u]
        v_node = G.nodes[v]
        lat, lon = get_edge_midpoint(u_node, v_node, data)
        
        traffic = None
        if query_count < max_queries:
            traffic = parse_tomtom_data(fetch_tomtom_data(lat, lon))
            query_count += 1

        length = float(data.get('length', 10.0))
        maxspeed_attr = data.get('maxspeed', 30.0)
        if isinstance(maxspeed_attr, list):
            maxspeed_attr = maxspeed_attr[0]
        try:
            default_speed = float(str(maxspeed_attr).split()[0])
        except (ValueError, TypeError):
            default_speed = 30.0
        # print("getting the tomtom coordiantes", traffic.get('coordinates'))
        # tomtom_line = LineString(traffic.get('coordinates'))
        # print(match_tomtom_segment( tomtom_line= tomtom_line,edges_gdf= edges ))
        
        if traffic and traffic['confidence'] > 0.4 and traffic['current_speed'] is not None:
            v_curr = float(traffic['current_speed'])
            v_free = float(traffic['free_flow_speed']) if traffic['free_flow_speed'] else default_speed
            is_closed = traffic['road_closure']
            has_data = True
            matched_edges += 1
        else:
            v_curr = default_speed * 0.7 
            v_free = default_speed
            is_closed = False
            has_data = False

        if v_curr <= 1.0:
            v_curr = 1.0

        data['v_current'] = v_curr
        data['v_free'] = v_free
        data['is_closed'] = is_closed
        data['has_traffic_data'] = has_data
        data['midpoint'] = (lat, lon)

    coverage = (matched_edges / len(G.edges)) * 100
    print(f"Traffic matching completed. API queries used: {query_count}. Coverage: {coverage:.2f}%")
    return G



# enrich_graph_with_traffic(load_graph())



#another method 

def initialize_traffic_attributes(G):
    for u, v, key, data in G.edges(keys=True,data=True):
        data["traffic_status"] = "unmatched"
        data["current_speed_kmh"] = None
        data["free_flow_speed_kmh"] = None
        data["traffic_time_s"] = None
        data["free_flow_time_s"] = None
        data["traffic_ratio"] = None
        data["traffic_color"] = "missing"
        data["is_closed"] = False
        
        
        


def apply_traffic_matches(G,matches):
    initialize_traffic_attributes(G)
    for edge_id, record in matches.items():
        u, v, key = edge_id
        # Verify that this exact edge exists.
        if not G.has_edge(u, v, key):
            print("Unknown edge:", edge_id)
            continue
        edge_data = G.edges[u, v, key]
        length_m = edge_data["length"]
        processed = process_traffic_record(record,length_m)
        edge_data.update({"current_speed_kmh": record.get("current_speed"),"free_flow_speed_kmh": record.get("free_flow_speed"),**processed})
    return G




def build_scenario_graph(G,scenario):
    if scenario not in ("free_flow", "traffic"):
        raise ValueError("Unknown scenario")
    H = G.copy()
    for u, v, key, data in list(H.edges(keys=True, data=True)):
        status = data.get("traffic_status")
        # Keep only valid measurements.
        if status != "valid":
            H.remove_edge(u, v, key)
            continue
        if data.get("is_closed", False):
            H.remove_edge(u, v, key)
            continue
        if scenario == "free_flow":
            cost = data.get("free_flow_time_s")
        else:
            cost = data.get("traffic_time_s")
        if cost is None or cost <= 0:
            H.remove_edge(u, v, key)
            continue
        # defining the cost for the data
        data["weight"] = float(cost)
    return H



from collections import Counter


def calculate_traffic_coverage(G):
    statuses = Counter(data.get("traffic_status", "unmatched") for _, _, _, data in G.edges(keys=True,data=True))
    total = G.number_of_edges()
    valid = statuses["valid"]
    coverage = (100 * valid / total if total > 0 else 0)
    return {
        "total_edges": total,
        "valid_edges": valid,
        "coverage_percent": coverage,
        "status_counts": dict(statuses)}




if __name__ == '__main__':
    matches = {
    (100, 200, 0): {
        "current_speed": 20,
        "free_flow_speed": 40,
        "confidence": 0.9,
        "road_closure": False},
    (200, 300, 0): {
        "current_speed": 35,
        "free_flow_speed": 40,
        "confidence": 0.95,
        "road_closure": False
    }}
    G_traffic = load_graph().copy()
    G_traffic = apply_traffic_matches(G_traffic,matches)
    
    coverage = calculate_traffic_coverage(G_traffic)
    print(coverage)