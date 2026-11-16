import osmnx as ox

from load_graph import load_graph
from graph_analysis import (
    inspect_node,
    find_nearest_node,
    find_nearest_edge,
    check_route_exists,
    get_reference_route
)


G = load_graph()

G_projected = ox.projection.project_graph(G)


latitude = 51.5215
longitude = -0.1300

# Find nearest node.
node = find_nearest_node(G, latitude, longitude)

inspect_node(G, node)

# Find nearest edge.
edge = find_nearest_edge(G_projected, latitude, longitude)

print("\nNearest road edge:", edge)