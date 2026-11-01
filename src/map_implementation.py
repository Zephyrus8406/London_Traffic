
# imports 
import osmnx as ox 
import networkx as nx
from pathlib import Path
import geopandas as gpd
import matplotlib.pyplot as plt


ox.settings.use_cache = True


def load_save_map(center =(51.5215, -0.1300) ,dist = 1000 ,path ='../data/map.gpkg' ):
    # getting the graph 
    # Download a 500-meter driving network
    G = ox.graph.graph_from_point(
        center,
        dist = dist,
        network_type="drive",
        simplify=False
    )
    
    # save to disk as GeoPackage file then plot
    # save street network as GraphML file to work with later in OSMnx or networkx or gephi
    ox.io.save_graphml(G, filepath="./data/network.graphml")
    fig, ax = ox.plot.plot_graph(G, node_size=0, edge_color="w", edge_linewidth=0.2)
    
    print("Nodes:", len(G.nodes))
    print("Edges:", len(G.edges))
    # calculate basic street network metrics and display average circuity
    stats = ox.stats.basic_stats(G)
    print(stats["circuity_avg"])
    # Display the network
    # identify endpoint nodes in red and nodes we'd remove in yellow
    nc = ["r" if ox.simplification._is_endpoint(G, node, None, None) else "y" for node in G.nodes()]
    fig, ax = ox.plot.plot_graph(G, node_color=nc)
    
    plt.show()
    


load_save_map()



