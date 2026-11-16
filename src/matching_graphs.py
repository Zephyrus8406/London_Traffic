from load_graph import load_graph
import osmnx as ox
import geopandas as gpd


G = load_graph()
G_projected = ox.projection.project_graph(G )
nodes_projected , edges_projected = ox.convert.graph_to_gdfs(G_projected )






