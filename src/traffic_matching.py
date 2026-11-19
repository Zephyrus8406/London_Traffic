import math

from shapely.geometry import LineString
from traffic_api import get_flow_segment , parse_flow_response
from load_graph import load_graph
from traffic_api import *

from collections import Counter

def calculate_heading(line):
    start = line.coords[0]
    end = line.coords[-1]
    
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    
    angle = math.degrees(math.atan2(dx, dy))
    return (angle + 360) % 360


def heading_difference(a, b):
    difference = abs(a - b)
    return min(difference,360 - difference)


# def geometry_overlap_ratio(tomtom_line,osm_line,tolerance=10):
#     road_buffer = osm_line.buffer(tolerance)
#     overlap = tomtom_line.intersection(road_buffer)
#     if tomtom_line.length == 0:return 0
#     return min(1.0,overlap.length / tomtom_line.length)
def geometry_overlap_ratio(tomtom_line,osm_line,tolerance=10):
    if osm_line is None or osm_line.is_empty or osm_line.length == 0:
        return 0.0
    tomtom_buffer = tomtom_line.buffer(tolerance)
    overlap = osm_line.intersection(tomtom_buffer)
    return min(1.0, overlap.length / osm_line.length)


def calculate_match_score(tomtom_line,osm_line):
    overlap = geometry_overlap_ratio(tomtom_line,osm_line)
    tomtom_heading = calculate_heading(tomtom_line)
    osm_heading = calculate_heading(osm_line)
    angle_diff = heading_difference(tomtom_heading,osm_heading)
    direction_similarity = (1 - angle_diff / 180)
    score = (0.7 * overlap+ 0.3 * direction_similarity)
    return score


def match_tomtom_segment(tomtom_line,edges_gdf,search_distance=25):
    search_area = tomtom_line.buffer(search_distance)
    candidate_positions = (edges_gdf.sindex.query(search_area,predicate="intersects"))
    candidates = edges_gdf.iloc[candidate_positions]
    if candidates.empty:
        return None
    results = []
    for edge_index, edge in candidates.iterrows():
        osm_line = edge.geometry
        score = calculate_match_score(tomtom_line,osm_line)
        results.append({"edge": edge_index,"score": score})
    results.sort(key=lambda item: item["score"],reverse=True)
    return results


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
    # matches = {
    # (100, 200, 0): {
    #     "current_speed": 20,
    #     "free_flow_speed": 40,
    #     "confidence": 0.9,
    #     "road_closure": False},
    # (200, 300, 0): {
    #     "current_speed": 35,
    #     "free_flow_speed": 40,
    #     "confidence": 0.95,
    #     "road_closure": False
    # }}
    G_traffic = load_graph().copy()

    real_edge = next(iter(G_traffic.edges(keys=True)))
    matches = {
        real_edge: {
            "current_speed": 20,
            "free_flow_speed": 40,
            "confidence": 0.9,
            "road_closure": False,
        }
    }
    G_traffic = apply_traffic_matches(G_traffic,matches)
    
    coverage = calculate_traffic_coverage(G_traffic)
    print(coverage)