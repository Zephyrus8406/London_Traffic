import osmnx as ox

from load_graph import load_graph
from traffic_api import *
from traffic_matching import *


G = load_graph()

matches = load_saved_matches()

G_traffic = G.copy()

G_traffic = apply_traffic_matches(G_traffic,matches)


coverage = calculate_traffic_coverage(G_traffic)

print("Traffic coverage:")
print(coverage)


G_freeflow = build_scenario_graph(G_traffic,"free_flow")
G_measured = build_scenario_graph(G_traffic,"traffic")

print("Original edges:", G.number_of_edges())
print("Free-flow edges:", G_freeflow.number_of_edges())
print("Traffic edges:", G_measured.number_of_edges())