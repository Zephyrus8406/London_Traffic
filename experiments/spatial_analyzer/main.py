# imports 
import geopandas as gpd
import matplotlib.pyplot as plt

from shapely.geometry import Point, LineString, Polygon

#create the roads 
roads = gpd.GeoDataFrame(
    {
        "road_name": [
            "Road A",
            "Road B",
            "Road C"
        ]
    },
    geometry=[
        LineString([(0, 0), (100, 0)]),
        LineString([(0, 50), (100, 50)]),
        LineString([(50, -20), (50, 80)])
    ],
    crs="EPSG:32630"
)


# Create buildings
buildings = gpd.GeoDataFrame(
    {
        "building_id": [1, 2, 3, 4]
    },
    geometry=[
        Polygon([(10, 10), (20, 10), (20, 20), (10, 20)]),
        Polygon([(60, 10), (70, 10), (70, 20), (60, 20)]),
        Polygon([(10, 60), (20, 60), (20, 70), (10, 70)]),
        Polygon([(80, 60), (90, 60), (90, 70), (80, 70)])
    ],
    crs="EPSG:32630"
)


#calculate road length 
roads['length'] = roads.geometry.length
print(roads[['length' , 'road_name' ]])


#create road buffers 
road_copy = roads.copy()
road_copy['geometry'] =( road_copy.geometry.buffer(15))

#find nearby buildings

nearby = gpd.sjoin(buildings , road_copy[['road_name',"geometry"]] , how = 'left' , predicate= 'intersects')
print(f'nearby buildings to the road or the intersections : {nearby}')


#project the road 
projected_roads = roads.to_crs('EPSG:32630')
projected_roads['buffer'] = projected_roads.geometry.buffer(100)
projected_roads.set_geometry(col = ['geometry' , 'buffer'])
print(projected_roads)


