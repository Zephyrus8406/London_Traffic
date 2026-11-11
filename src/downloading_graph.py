
#we are going to first download the osmnx graph file and then load it from that same place 
# so here we are going to define the function to download it we are putting it alone here because we are going to just call and use it once 

#imports 
from pathlib import Path
import osmnx as ox
import os 

#ASSETS
GRAPH_PATH = './data/graph/london.graphml'
CENTER = (51.5215, -0.1300)
DISTANCE = 750


def download_and_save_graph(center=CENTER,distance=DISTANCE,save_path=GRAPH_PATH):
    """
    Download a drivable OSM graph and save it as GraphML.
    """
    if Path.exists(save_path):
        save_path = Path(save_path)
    else :
        raise ValueError('the path specified doesnt exist')
    # Create directory if it doesn't exist
    save_path.parent.mkdir(parents=True,exist_ok=True)
    print("Downloading road network...")
    G = ox.graph_from_point(center,dist=distance,network_type="drive",simplify=True)
    print("Download complete.")
    print(f"Nodes: {len(G.nodes)}")
    print(f"Edges: {len(G.edges)}")
    
    # Save graph
    ox.save_graphml(G,filepath=save_path)
    print(f"Graph saved to: {save_path}")
    return G




download_and_save_graph()