
#imports 

import osmnx as ox 
from shapely.geometry import Point
import networkx
import geopandas as gpd 


#inspection 
def inspect_node(G , node):
    print(f'\n node id: {node}')
    print(f'\n node attributes : {G.nodes[node]}')
    
    print('----------------------------------------')
    print('\n out going edges ')
    for u , v ,key , data in G.out_edges(node , keys = True , data = True):
        print(f'{u} --> {v} , \n key = {key} , \n length : {data.get('length')}')
        
        
    print('----------------------------------------')
    print('\n in going edges ')
    for u , v , key ,data in G.in_edges(node , keys = True , data = True):
        print(f'{u} --> {v} , \n key = {key} , \n length : {data.get('length')}')
        

def find_nearest_node(G,latitude , longitude):
    return ox.distance.nearest_nodes(G , X =longitude , Y = latitude)


def find_nearest_edge(G_projected , latitude , longitude):
    point = gpd.GeoSeries([Point(longitude , latitude)] , crs = 'EPSG:4326')
    projected_point = point.to_crs(G_projected.graph['crs'])
    x = projected_point.iloc[0].x
    y = projected_point.iloc[0].y
    
    return ox.distance.nearest_edges(G_projected , X = x , Y= y)


def check_route_exists(G, origin, destination):
    return nx.has_path(G, origin, destination)


def get_reference_route(G, origin, destination):
    if not check_route_exists(G, origin, destination):
        raise nx.NetworkXNoPath(
            "No directed route exists."
        )

    return nx.shortest_path(
        G,
        source=origin,
        target=destination,
        weight="length",
        method="dijkstra"
    )





