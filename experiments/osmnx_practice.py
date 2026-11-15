
#imports

import osmnx as ox
import matplotlib.pyplot as plt 





CENTER_POINT = (51.5215, -0.1300)
G = ox.graph.graph_from_point(center_point= CENTER_POINT , dist= 750 , network_type= 'drive' , simplify= True)
print(f'''
    number of edges {len(G.edges)}
    number of nodes {len(G.nodes)}
    is directed : {G.is_directed()}
    
    ''')

print(f'edges sample : {list(G.edges)[0]}')
print(f" nodes sample : {list(G.nodes)[0]}")


print(f'edges analysis : {G.edges[list(G.edges)[0]]}')
print(f" nodes analysis : {G.nodes[list(G.nodes)[0]]}")

nodes , edges = ox.graph_to_gdfs(G,nodes= True , edges= True , fill_edge_geometry= True)


print(f'samples of geopandas edges : {edges.head(5)}')
print(f'samples of geopandas nodes : {nodes.head(5)}')

print(f'inspecting the edges : {edges.index.names}')


print(f'edges data : {edges.loc[(104302,107844,0)]}')
print(f'edges shape : {edges.shape}')
print(f'edges data : {edges.iloc[0]}')

print(f'getting the graph edges information : {edges[['length', 'highway' , 'geometry']].head()}')


nodes_projected = nodes.to_crs(
    nodes.estimate_utm_crs()
)

edges_projected = edges.to_crs(
    nodes_projected.crs
)

#now we can even project the graph 
G_projected = ox.projection.project_graph(G)

print(f'projected graph : { G_projected}')

#now convert this projected graph 
nodes_projected , edges_projected = nodes, edges = ox.convert.graph_to_gdfs(
    G_projected,
    nodes=True,
    edges=True,
    node_geometry=True,
    fill_edge_geometry=True
)

edges_projected['edges_length'] = edges_projected.geometry.length

print(f'''
    --------------------------------------
    
    lets inspect the projected geapandas :
    projected nodes :  {nodes_projected.head()}
    projected edges :  {edges_projected.head()}
    
    edges : {edges.crs}
    projected edges : {edges_projected.crs}
    length : {edges_projected["edges_length"]}
    
    
    ---------------------------------------
    ''' )


#visualize it 
fig, ax = ox.plot.plot_graph(
    G,
    node_size=8,
    edge_linewidth=1,
    bgcolor="white",
    show=False,
    close=False
)

plt.show()


fig, ax = plt.subplots(figsize=(12, 10))

edges_projected.plot(
    ax=ax,
    linewidth=1,
    color="steelblue"
)

nodes_projected.plot(
    ax=ax,
    color="red",
    markersize=5
)

ax.set_title("Bloomsbury Road Network")

plt.show()


def graph_visual(G,node_size = 8, edges_line_width = 1 , bgcolor = 'white'):
    fix , ax = ox.plot.plot_graph(G, node_size= node_size ,edge_linewidth= edges_line_width , bgcolor= bgcolor , 
                                show= False , close= False)
    
    plt.show()
    



print("Graph type:", type(G))
print("Directed:", G.is_directed())
print("Multigraph:", G.is_multigraph())


print("\nNetwork statistics")

print("Nodes:", len(nodes))
print("Edges:", len(edges))

print(
    "Total road length:",
    edges["length"].sum() / 1000,
    "km"
)


#  Find the longest edges

longest_edges = edges_projected.nlargest(
    10,
    "length"
)


