'''create two roads, a GPS location, calculate their lengths, find their midpoints, calculate their distance, and create a buffer.'''

#imports 
from shapely.geometry import LineString , Point
from shapely.ops import nearest_points
import geopandas as  gpd
import matplotlib.pyplot as plt


#create tow roads 
road_1 = LineString([(0, 0),
    (100, 50),
    (200, 50)])

road_2 = LineString([(0, 20),
    (100, 70),
    (200, 70)])

#create the locations 
location = Point(100, 65)

#calculate their length 
print(f'length of the road_1 : {road_1.length}')
print(f'length of the road_2 : {road_2.length}')

#find their midpoint 
print(f'raod_1 midpoint : {road_1.interpolate(0.5 , normalized= True)}')
print(f'raod_2 midpoint : {road_2.interpolate(0.5 , normalized= True)}')

#distance between the roads 
print(f'distance between the two roads : {road_1.distance(road_2)}')

#find the nearest node on the road to that location 
print(f'the nearest node on the road to that location :{nearest_points(road_1 , location)[0]}')

#create a buffer around  road 1
buffer = road_1.buffer(30)
print(f" the buffer around the road_1 by 30 units : {buffer}")


#containment and the within functions 
print(f'''
    raod_1 contains the location  : {road_1.contains(location)} , 
    and the location is within the road_1 : {location.within(road_1)} 
    ''')


#create a geopandas object 
gdf = gpd.GeoDataFrame({"name": ["road A","road B","GPS Location"]},geometry=[road_1, road_2, location],crs="EPSG:32630")
print(gdf)


#visualize 
ax = gdf.iloc[:2].plot(color= 'blue' , linewidth= 4 , figsize= (10,10))

gpd.GeoDataFrame(geometry = gdf.buffer(30) , crs = gdf.crs).boundary.plot(ax=ax,color="red",linestyle="--")

gdf.iloc[[2]].plot(ax=ax,color="orange",markersize=80)

ax.set_title("Road Geometry Analyzer")

plt.show()