from load_graph import load_graph
import osmnx as ox
import geopandas as gpd
import math




def geometry_overlap_ratio(tomtom_line,osm_line,tolerance=10):
    road_buffer = osm_line.buffer(tolerance)

    overlap = tomtom_line.intersection(road_buffer)

    if tomtom_line.length == 0:
        return 0

    return min(1.0,overlap.length / tomtom_line.length)




def calculate_match_score(tomtom_line,osm_line):
    overlap = geometry_overlap_ratio(tomtom_line,osm_line)
    tomtom_heading = calculate_heading(tomtom_line)
    osm_heading = calculate_heading(osm_line)
    angle_diff = heading_difference(tomtom_heading,osm_heading)
    direction_similarity = (1 - angle_diff / 180)
    score = (0.7 * overlap+ 0.3 * direction_similarity)
    return score



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


def geometry_overlap_ratio(tomtom_line,osm_line,tolerance=10):
    road_buffer = osm_line.buffer(tolerance)
    overlap = tomtom_line.intersection(road_buffer)
    if tomtom_line.length == 0:return 0
    return min(1.0,overlap.length / tomtom_line.length)

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
