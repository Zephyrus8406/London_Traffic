
# imports 
import osmnx as ox 
import networkx as nx
from pathlib import Path
import geopandas as gpd
import matplotlib.pyplot as plt

def load_save_map(center ,dist ,path ='../data' ):
    # getting the graph 
    # Download a 500-meter driving network
    G = ox.graph.graph_from_point(
        center,
        dist = dist,
        network_type="drive",
        simplify=True
    )
    
    # save to disk as GeoPackage file then plot
    ox.io.save_graph_geopackage(G , path)
    fig, ax = ox.plot.plot_graph(G, node_size=0, edge_color="w", edge_linewidth=0.2)
    
    
    
# Enable caching to avoid repeatedly downloading data
ox.settings.use_cache = True

# King's Cross approximate center

center = (51.5215, -0.1300)
# Download a 500-meter driving network
G = ox.graph.graph_from_point(
    center,
    dist=500,
    network_type="drive",
    simplify=True
)


print("Nodes:", len(G.nodes))
print("Edges:", len(G.edges))

# Display the network
ox.plot.plot_graph(G)
plt.show()