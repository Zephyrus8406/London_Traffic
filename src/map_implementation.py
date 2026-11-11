
# imports 
import osmnx as ox 
import networkx as nx
from pathlib import Path
import geopandas as gpd
import matplotlib.pyplot as plt

import osmnx as ox
import networkx as nx
import os

def load_or_create_map(center_point=(51.4988, -0.1749), dist=1000, filepath="data/London.graphml"):
    """
    دانلود گراف معابر رانندگی لندن به صورت جهت‌دار و ذخیره محلی آن.
    """
    if os.path.exists(filepath):
        print(f"Loading existing graph from {filepath}...")
        G = ox.load_graphml(filepath)
        return G

    print("Fetching driving graph from OpenStreetMap...")
    # دانلود گراف معابر رانندگی به صورت پیش‌فرض MultiDiGraph
    G = ox.graph_from_point(center_point, dist=dist, network_type='drive')
    
    # افزودن طول واقعی خیابان‌ها به متر
    G = ox.distance.add_edge_lengths(G)
    
    # اطمینان از وجود پوشه data
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    ox.save_graphml(G, filepath)
    print(f"Graph saved to {filepath} with {len(G.nodes)} nodes and {len(G.edges)} edges.")
    return G

if __name__ == "__main__":
    load_or_create_map()

#### traffic_api ###

# import requests
# import os
# from dotenv import load_dotenv

# load_dotenv()
# TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY")

# def fetch_flow_segment(lat, lon, api_key=TOMTOM_API_KEY):
#     """
#     دریافت اطلاعات لحظه‌ای سگمنت ترافیکی بر اساس مختصات نقطه میانی خیابان.
#     """
#     if not api_key:
#         raise ValueError("TomTom API key not found. Please set TOMTOM_API_KEY in .env file.")

#     url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/relative0/10/json"
#     params = {
#         'point': f"{lat},{lon}",
#         'unit': 'KMPH',
#         'key': api_key
#     }
    
#     try:
#         response = requests.get(url, params=params, timeout=5)
#         if response.status_code == 200:
#             data = response.json().get('flowSegmentData', {})
#             return {
#                 'current_speed': data.get('currentSpeed'),       # km/h
#                 'free_flow_speed': data.get('freeFlowSpeed'),   # km/h
#                 'confidence': data.get('confidence', 0.0),       # اعتبارسنجی ۰ تا ۱
#                 'road_closure': data.get('roadClosure', False),  # انسداد جاده
#                 'coordinates': data.get('coordinates', {}).get('coordinate', [])
#             }
#         elif response.status_code == 403:
#             print("API Limit Exceeded or Invalid Key.")
#             return None
#         else:
#             return None
#     except Exception as e:
#         print(f"Request failed: {e}")
#         return None

### traffic_matching ###

# from shapely.geometry import LineString
# from src.traffic_api import fetch_flow_segment

# def get_edge_midpoint(u_data, v_data, edge_data):
#     """
#     محاسبه مختصات جغرافیایی (lat, lon) نقطه میانی یال.
#     """
#     if 'geometry' in edge_data:
#         geom = edge_data['geometry']
#         midpoint = geom.interpolate(0.5, normalized=True)
#         return midpoint.y, midpoint.x
#     else:
#         mid_lat = (u_data['y'] + v_data['y']) / 2.0
#         mid_lon = (u_data['x'] + v_data['x']) / 2.0
#         return mid_lat, mid_lon

# def enrich_graph_with_traffic(G, max_queries=150):
#     """
#     اعمال داده‌های TomTom روی یال‌های گراف با رعایت محدودیت سقف درخواست روزانه.
#     """
#     query_count = 0
#     matched_edges = 0

#     for u, v, k, data in G.edges(keys=True, data=True):
#         u_node = G.nodes[u]
#         v_node = G.nodes[v]
#         lat, lon = get_edge_midpoint(u_node, v_node, data)
        
#         traffic = None
#         if query_count < max_queries:
#             traffic = fetch_flow_segment(lat, lon)
#             query_count += 1

#         # مقداردهی پیش‌فرض در صورت نبود یا عدم اعتبار داده
#         length = float(data.get('length', 10.0))
#         maxspeed_attr = data.get('maxspeed', 30.0)
#         if isinstance(maxspeed_attr, list):
#             maxspeed_attr = maxspeed_attr[0]
#         try:
#             default_speed = float(str(maxspeed_attr).split()[0])
#         except (ValueError, TypeError):
#             default_speed = 30.0

#         if traffic and traffic['confidence'] > 0.4 and traffic['current_speed'] is not None:
#             v_curr = float(traffic['current_speed'])
#             v_free = float(traffic['free_flow_speed']) if traffic['free_flow_speed'] else default_speed
#             is_closed = traffic['road_closure']
#             has_data = True
#             matched_edges += 1
#         else:
#             # داده مفقود به معنی روان بودن نیست؛ سرعت پیش‌فرض با جریمه محتاطانه لحاظ می‌شود
#             v_curr = default_speed * 0.7 
#             v_free = default_speed
#             is_closed = False
#             has_data = False

#         # پیشگیری از سرعت صفر
#         if v_curr <= 1.0:
#             v_curr = 1.0

#         data['v_current'] = v_curr
#         data['v_free'] = v_free
#         data['is_closed'] = is_closed
#         data['has_traffic_data'] = has_data
#         data['midpoint'] = (lat, lon)

#     coverage = (matched_edges / len(G.edges)) * 100
#     print(f"Traffic matching completed. API queries used: {query_count}. Coverage: {coverage:.2f}%")
#     return G

### graph_weights ###
# def assign_weights(G, scenario="traffic"):
#     """
#     تخصیص وزن‌های زمانی و مسافتی برای سناریوهای: free_flow, traffic, closure
#     """
#     max_speed_found = 1.0

#     for u, v, k, data in G.edges(keys=True, data=True):
#         length = float(data.get('length', 1.0))
        
#         if scenario == "free_flow":
#             speed = data.get('v_free', 30.0)
#         else:
#             speed = data.get('v_current', 30.0)

#         # انسداد جاده در سناریوی closure یا در صورت تأیید بسته بودن از سوی API
#         if data.get('is_closed', False) or (scenario == "closure" and data.get('manual_closure', False)):
#             cost_time = float('inf')
#             cost_distance = float('inf')
#         else:
#             cost_time = (3.6 * length) / speed  # فرمول زمان بر حسب ثانیه
#             cost_distance = length

#         data['weight_time'] = cost_time
#         data['weight_distance'] = cost_distance

#         if speed > max_speed_found and speed != float('inf'):
#             max_speed_found = speed

#     return G, max_speed_found

### search_algorithm ###
# from collections import deque
# import heapq
# from geopy.distance import geodesic
# import time

# def heuristic(node, goal, G, objective, v_max):
#     """
#     تابع هیوریستیک پذیرفتنی (Admissible):
#     - در مسافت: فاصله ژئودزیک مستقیم d(n, G)
#     - در زمان: (3.6 * d(n, G)) / V_max
#     """
#     n_coord = (G.nodes[node]['y'], G.nodes[node]['x'])
#     g_coord = (G.nodes[goal]['y'], G.nodes[goal]['x'])
#     dist_meters = geodesic(n_coord, g_coord).meters

#     if objective == 'distance':
#         return dist_meters
#     elif objective == 'time':
#         return (3.6 * dist_meters) / v_max
#     return 0.0

# def reconstruct_path(came_from, current):
#     path = [current]
#     while current in came_from:
#         current = came_from[current]
#         path.append(current)
#     path.reverse()
#     return path

# def run_search(algorithm, G, start, goal, objective='time', v_max=50.0):
#     weight_key = 'weight_time' if objective == 'time' else 'weight_distance'
    
#     start_time = time.perf_counter()
#     nodes_expanded = 0
#     max_frontier_size = 0
#     came_from = {}
    
#     # ------------------ BFS ------------------
#     if algorithm == 'BFS':
#         frontier = deque([start])
#         explored = set([start])
#         while frontier:
#             max_frontier_size = max(max_frontier_size, len(frontier))
#             curr = frontier.popleft()
#             nodes_expanded += 1
            
#             if curr == goal:
#                 path = reconstruct_path(came_from, curr)
#                 return path, nodes_expanded, max_frontier_size, time.perf_counter() - start_time
            
#             # شکستن تساوی بر اساس مقدار شناسه گره
#             for nxt in sorted(G.neighbors(curr)):
#                 edge_cost = min([d.get(weight_key, float('inf')) for d in G.get_edge_data(curr, nxt).values()])
#                 if edge_cost != float('inf') and nxt not in explored:
#                     explored.add(nxt)
#                     came_from[nxt] = curr
#                     frontier.append(nxt)

#     # ------------------ DFS ------------------
#     elif algorithm == 'DFS':
#         frontier = [start]
#         explored = set()
#         while frontier:
#             max_frontier_size = max(max_frontier_size, len(frontier))
#             curr = frontier.pop()
            
#             if curr in explored:
#                 continue
#             explored.add(curr)
#             nodes_expanded += 1
            
#             if curr == goal:
#                 path = reconstruct_path(came_from, curr)
#                 return path, nodes_expanded, max_frontier_size, time.perf_counter() - start_time
            
#             for nxt in sorted(G.neighbors(curr), reverse=True):
#                 edge_cost = min([d.get(weight_key, float('inf')) for d in G.get_edge_data(curr, nxt).values()])
#                 if edge_cost != float('inf') and nxt not in explored:
#                     came_from[nxt] = curr
#                     frontier.append(nxt)

#     # ---------- Greedy Best-First Search ----------
#     elif algorithm == 'Greedy':
#         counter = 0
#         h_start = heuristic(start, goal, G, objective, v_max)
#         frontier = [(h_start, counter, start)]
#         explored = set()
        
#         while frontier:
#             max_frontier_size = max(max_frontier_size, len(frontier))
#             h_val, _, curr = heapq.heappop(frontier)
            
#             if curr in explored:
#                 continue
#             explored.add(curr)
#             nodes_expanded += 1
            
#             if curr == goal:
#                 path = reconstruct_path(came_from, curr)
#                 return path, nodes_expanded, max_frontier_size, time.perf_counter() - start_time
            
#             for nxt in sorted(G.neighbors(curr)):
#                 edge_cost = min([d.get(weight_key, float('inf')) for d in G.get_edge_data(curr, nxt).values()])
#                 if edge_cost != float('inf') and nxt not in explored:
#                     came_from[nxt] = curr
#                     counter += 1
#                     h_next = heuristic(nxt, goal, G, objective, v_max)
#                     heapq.heappush(frontier, (h_next, counter, nxt))

#     # ------------------ A* ------------------
#     elif algorithm == 'A*':
#         counter = 0
#         g_score = {start: 0.0}
#         h_start = heuristic(start, goal, G, objective, v_max)
#         frontier = [(h_start, counter, start)]
#         explored = set()

#         while frontier:
#             max_frontier_size = max(max_frontier_size, len(frontier))
#             f_val, _, curr = heapq.heappop(frontier)
            
#             if curr in explored:
#                 continue
#             explored.add(curr)
#             nodes_expanded += 1
            
#             if curr == goal:
#                 path = reconstruct_path(came_from, curr)
#                 return path, nodes_expanded, max_frontier_size, time.perf_counter() - start_time
            
#             for nxt in sorted(G.neighbors(curr)):
#                 edge_cost = min([d.get(weight_key, float('inf')) for d in G.get_edge_data(curr, nxt).values()])
#                 if edge_cost == float('inf'):
#                     continue
                
#                 tentative_g = g_score[curr] + edge_cost
#                 if tentative_g < g_score.get(nxt, float('inf')):
#                     came_from[nxt] = curr
#                     g_score[nxt] = tentative_g
#                     counter += 1
#                     f_score = tentative_g + heuristic(nxt, goal, G, objective, v_max)
#                     heapq.heappush(frontier, (f_score, counter, nxt))

#     return None, nodes_expanded, max_frontier_size, time.perf_counter() - start_time

### metrics ###
# def compute_path_costs(path, G):
#     """
#     محاسبه مجموع مسافت و مجموع زمان سفر در امتداد یک مسیر بازگشتی.
#     """
#     if not path or len(path) < 2:
#         return float('inf'), float('inf')
        
#     total_distance = 0.0
#     total_time = 0.0
    
#     for i in range(len(path) - 1):
#         u, v = path[i], path[i + 1]
#         edge_dict = G.get_edge_data(u, v)
#         # انتخاب لبه با کمترین هزینه در حالت Multi-edge
#         min_time_edge = min(edge_dict.values(), key=lambda d: d.get('weight_time', float('inf')))
#         total_time += min_time_edge.get('weight_time', float('inf'))
#         total_distance += min_time_edge.get('weight_distance', float('inf'))
        
#     return total_distance, total_time

### experiments ###
# import numpy as np
# import pandas as pd
# from src.search_algorithm import run_search
# from src.metrics import compute_path_costs
# from src.graph_weights import assign_weights

# def run_all_experiments(G, origins, destination, v_max):
#     algorithms = ['BFS', 'DFS', 'Greedy', 'A*']
#     scenarios = ['free_flow', 'traffic', 'closure']
#     objectives = ['distance', 'time']
#     records = []

#     for scen in scenarios:
#         G_scen, current_v_max = assign_weights(G, scenario=scen)
#         for obj in objectives:
#             for orig in origins:
#                 for algo in algorithms:
#                     runtimes = []
#                     # اجرای ۵ باره جهت محاسبه میانه زمان اجرا
#                     for _ in range(5):
#                         path, expanded, max_f, runtime = run_search(
#                             algo, G_scen, orig, destination, objective=obj, v_max=current_v_max
#                         )
#                         runtimes.append(runtime)
                    
#                     median_time = float(np.median(runtimes))
#                     dist, cost_t = compute_path_costs(path, G_scen)
                    
#                     records.append({
#                         'Scenario': scen,
#                         'Objective': obj,
#                         'Origin': orig,
#                         'Algorithm': algo,
#                         'Path_Found': path is not None,
#                         'Distance_m': dist,
#                         'Travel_Time_s': cost_t,
#                         'Median_Runtime_s': median_time,
#                         'Node_Expansions': expanded,
#                         'Max_Frontier_Size': max_f
#                     })

#     df = pd.DataFrame(records)
#     df.to_csv("data/expriment_result.csv", index=False)
#     print("Experiments completed and saved to data/expriment_result.csv")
#     return df

### visualization ###
# import folium

# def visualize_routes_and_traffic(G, paths_dict, destination_node, output_file="data/map.html"):
#     """
#     تولید فایل HTML نقشه با تفکیک لایه‌های ترافیکی و مسیرهای ۴ الگوریتم.
#     """
#     dest_lat = G.nodes[destination_node]['y']
#     dest_lon = G.nodes[destination_node]['x']
#     m = folium.Map(location=[dest_lat, dest_lon], zoom_start=15)

#     # 1. لایه ترافیک TomTom
#     traffic_fg = folium.FeatureGroup(name="TomTom Traffic Overlay", show=True)
#     for u, v, k, data in G.edges(keys=True, data=True):
#         if not data.get('has_traffic_data', False):
#             continue
#         v_curr = data.get('v_current', 30.0)
#         v_free = data.get('v_free', 30.0)
#         r = v_curr / v_free if v_free > 0 else 1.0

#         if r < 0.5:
#             color = 'red'
#         elif 0.5 <= r <= 0.8:
#             color = 'yellow'
#         else:
#             continue  # بدون ترافیک

#         pts = [(G.nodes[u]['y'], G.nodes[u]['x']), (G.nodes[v]['y'], G.nodes[v]['x'])]
#         folium.PolyLine(pts, color=color, weight=4, opacity=0.8).add_to(traffic_fg)
#     traffic_fg.add_to(m)

#     # 2. لایه‌های مجزا برای مسیر هر الگوریتم
#     algo_colors = {'BFS': 'blue', 'DFS': 'purple', 'Greedy': 'orange', 'A*': 'green'}
#     for algo_name, path in paths_dict.items():
#         if not path:
#             continue
#         fg = folium.FeatureGroup(name=f"Path: {algo_name}", show=True)
#         path_coords = [(G.nodes[node]['y'], G.nodes[node]['x']) for node in path]
#         folium.PolyLine(
#             path_coords, 
#             color=algo_colors.get(algo_name, 'black'), 
#             weight=5, 
#             opacity=0.9
#         ).add_to(fg)
#         fg.add_to(m)

#     # علامت‌گذاری مقصد
#     folium.Marker(
#         [dest_lat, dest_lon],
#         popup="Destination",
#         icon=folium.Icon(color="red", icon="star")
#     ).add_to(m)

#     # قابلیت کلیک برای افزودن مختصات مبدأ
#     m.add_child(folium.ClickForMarker(popup="Selected Origin"))
#     folium.LayerControl().add_to(m)
#     m.save(output_file)
#     print(f"Interactive map generated at {output_file}")

####