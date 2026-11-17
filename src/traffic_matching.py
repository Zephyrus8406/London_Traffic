from shapely.geometry import LineString
from traffic_api import fetch_tomtom_data , parse_tomtom_data
from load_graph import load_graph
from matching_graphs import *


def get_edge_midpoint(u_data, v_data, edge_data):
    
    if 'geometry' in edge_data:
        geom = edge_data['geometry']
        midpoint = geom.interpolate(0.5, normalized=True)
        return midpoint.y, midpoint.x
    else:
        mid_lat = (u_data['y'] + v_data['y']) / 2.0
        mid_lon = (u_data['x'] + v_data['x']) / 2.0
        return mid_lat, mid_lon



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



enrich_graph_with_traffic(load_graph())