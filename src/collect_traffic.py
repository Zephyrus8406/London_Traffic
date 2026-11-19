import time
from datetime import datetime, timezone

import geopandas as gpd
import osmnx as ox

from load_graph import load_graph
from traffic_api import get_flow_segment, parse_flow_response, save_matches
from traffic_matching import (apply_traffic_matches, calculate_traffic_coverage, match_tomtom_segment)

SNAPSHOT_PATH = "./data/traffic_snapshot.json"
MAX_QUERIES = 200
MIN_MATCH_SCORE = 0.55     

# def get_edge_midpoint(G, u_data, v_data, edge_data):
    
#     if 'geometry' in edge_data:
#         geom = edge_data['geometry']
#         midpoint = geom.interpolate(0.5, normalized=True)
#         return midpoint.y, midpoint.x
#     else:
#         mid_lat = (u_data['y'] + v_data['y']) / 2.0
#         mid_lon = (u_data['x'] + v_data['x']) / 2.0
#         return mid_lat, mid_lon

def get_edge_midpoint_latlon(G, u, v, data):
    if "geometry" in data and data["geometry"] is not None:
        mid = data["geometry"].interpolate(0.5, normalized=True)
        return mid.y, mid.x
    lat = (G.nodes[u]["y"] + G.nodes[v]["y"]) / 2.0
    lon = (G.nodes[u]["x"] + G.nodes[v]["x"]) / 2.0
    return lat, lon

def project_line_to_crs(line, target_crs):
    return gpd.GeoSeries([line], crs="EPSG:4326").to_crs(target_crs).iloc[0]


def collect_and_save_snapshot(snapshot_path=SNAPSHOT_PATH, max_queries=MAX_QUERIES, min_score=MIN_MATCH_SCORE):
    G = load_graph()

    G_proj = ox.projection.project_graph(G)
    target_crs = G_proj.graph["crs"]
    edges_gdf = ox.convert.graph_to_gdfs(G_proj, nodes=False, edges=True)

    matches = {}
    query_count = 0
    start_time = datetime.now(timezone.utc)
    print(f"Collection started at: {start_time.isoformat()}")

    for u, v, key, data in G.edges(keys=True, data=True):
        if query_count >= max_queries:
            print(f"Reached max_queries limit ({max_queries}). Stopping.")
            break

        if (u, v, key) in matches:
            continue

        lat, lon = get_edge_midpoint_latlon(G, u, v, data)
        raw_data = get_flow_segment(latitude=lat, longitude=lon)
        query_count += 1

        if not raw_data:
            continue

        try:
            record = parse_flow_response(raw_data)
        except ValueError:
            continue

        tomtom_line = record.get("geometry")
        if tomtom_line is None or tomtom_line.is_empty:
            continue

        tomtom_line_proj = project_line_to_crs(tomtom_line, target_crs)
        candidates = match_tomtom_segment(tomtom_line_proj, edges_gdf)

        if not candidates:
            continue

        json_safe_record = {k: val for k, val in record.items() if k != "geometry"}

        for item in candidates:
            edge_id = item["edge"]  # (u, v, key)
            score = item["score"]
            if score >= min_score and edge_id not in matches:
                matches[edge_id] = json_safe_record

        time.sleep(0.1)

        if query_count % 25 == 0:
            print(f"Queries: {query_count}/{max_queries} | Matched edges: {len(matches)}")

    end_time = datetime.now(timezone.utc)
    print(f"Collection finished at: {end_time.isoformat()}")
    print(f"Collection interval: {(end_time - start_time).total_seconds():.1f} seconds")

    save_matches(matches, snapshot_path)

    G_check = apply_traffic_matches(G.copy(), matches)
    coverage = calculate_traffic_coverage(G_check)
    print("Final Traffic Coverage:", coverage)


if __name__ == "__main__":
    collect_and_save_snapshot()