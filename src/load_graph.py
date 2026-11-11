#imports 
from pathlib import Path
import osmnx as ox

#ASSETS
GRAPH_PATH = './data/graph/london.graphml'

def load_graph(graph_path=GRAPH_PATH):
    """
    Load an existing OSM graph from a GraphML file.
    """
    graph_path = Path(graph_path)
    if not graph_path.exists():
        raise FileNotFoundError(f"Graph file not found: {graph_path}")
    print("Loading saved graph...")
    G = ox.load_graphml(graph_path)
    print("Graph loaded successfully.")
    print(f"Nodes: {len(G.nodes)}")
    print(f"Edges: {len(G.edges)}")
    return G

if __name__ == '__main__':
    load_graph()