
#imports

import osmnx as os


CENTER_POINT = (51.5215, -0.1300)
G = os.graph.graph_from_point(center_point= CENTER_POINT , dist= 750 , network_type= 'drive' , simplify= True)
print(f'''
    number of edges {len(G.edges)}
    number of nodes {len(G.nodes)}
    is directed : {G.is_directed()}
    
    ''')

print(f'edges sample : {list(G.edges)[0]}')
print(f" nodes sample : {list(G.nodes)[0]}")


print(f'edges analysis : {G.edges[list(G.edges)[0]]}')
print(f" nodes analysis : {G.nodes[list(G.nodes)[0]]}")

nodes , edges = os.graph_to_gdfs(G,nodes= True , edges= True , fill_edge_geometry= True)


print(f'samples of geopandas edges : {edges.head(5)}')
print(f'samples of geopandas nodes : {nodes.head(5)}')

print(f'inspecting the edges : {edges.index.names}')


print(f'edges data : {edges.loc[(104302,107844,0)]}')
print(f'edges shape : {edges.shape}')
print(f'edges data : {edges.iloc[0]}')

print(f'getting the graph edges information : {edges[['length', 'highway' , 'geometry']].head()}')

#now we can even project the graph 
G_projected = os.projection.project_graph(G)

print(f'projected graph : { G_projected}')

#now convert this projected graph 


