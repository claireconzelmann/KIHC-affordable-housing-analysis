import pandas as pd
import geopandas as gpd
from shapely import wkt
import os
from shapely.geometry import Point
import ast  

path = "/Users/claireconzelmann/Documents/GitHub/KIHC-affordable-housing-analysis"

tif_districts = pd.read_csv(os.path.join(path, "Data/Raw/Boundaries_Tax_Increment_Financing_Districts.csv"))
city_land = pd.read_csv(os.path.join(path, "Data/Raw/City-Owned_Land_Inventory_20250320.csv"))
l_stops = pd.read_csv(os.path.join(path, "Data/Raw/CTA_System_Information_List_of_L_Stops.csv"))
bus_stops_gdf = gpd.read_file(os.path.join(path, "Data/Raw/CTA_BusStops.shp"))
metra_stops_gdf = gpd.read_file(os.path.join(path, "Data/Raw/MetraStations.shp"))

#create geopandas objects
tif_districts["the_geom"] = tif_districts["the_geom"].apply(wkt.loads)
tif_districts_gdf = gpd.GeoDataFrame(tif_districts, geometry="the_geom")
tif_districts_gdf = tif_districts_gdf.set_crs(epsg=4326, inplace=True)

city_land_gpd = gpd.GeoDataFrame(city_land, 
                                 geometry=gpd.points_from_xy(city_land.Longitude, 
                                                             city_land.Latitude), 
                                 crs="EPSG:4326")

# Convert string representation of tuples of long/lat in lstop data into actual tuples
l_stops["Location"] = l_stops["Location"].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) else x)

l_stops["geometry"] = l_stops["Location"].apply(lambda x: Point(x[1], x[0]))
l_stops_gdf = gpd.GeoDataFrame(l_stops, geometry="geometry")
l_stops_gdf.set_crs(epsg=4326, inplace=True)

bus_stops_gdf.set_crs(epsg=4326, inplace=True)
metra_stops_gdf.to_crs(epsg=4326, inplace=True)

#filtering metra stops to chicago only
metra_stops_gdf = metra_stops_gdf.loc[metra_stops_gdf["MUNICIPALI"]=="Chicago"]

#create 1/2 mile buffers around CTA and Metra stops (ETOD eligible)
metra_stops_gdf = metra_stops_gdf.to_crs(epsg=3857)
metra_stops_gdf["buffer_half_mile"] = metra_stops_gdf.geometry.buffer(804.67)
metra_stops_gdf = metra_stops_gdf.to_crs(epsg=4326)

l_stops_gdf = l_stops_gdf.to_crs(epsg=3857)
l_stops_gdf["buffer_half_mile"] = l_stops_gdf.geometry.buffer(804.67)
l_stops_gdf = l_stops_gdf.to_crs(epsg=4326)

#find vacant city owned lots within 1/2 buffers of transit stations
etod_lots_l = gpd.sjoin(city_land_gpd, 
                        l_stops_gdf.set_geometry("buffer_half_mile").to_crs(epsg=4326), 
                        predicate="within")

etod_lots_metra = gpd.sjoin(city_land_gpd, 
                        metra_stops_gdf.set_geometry("buffer_half_mile").to_crs(epsg=4326), 
                        predicate="within")

etod_lots = pd.concat([etod_lots_l, etod_lots_metra], ignore_index=True).drop_duplicates(subset=["ID"])
etod_lots = etod_lots.drop("index_right", axis=1)

#find etod eligible lots that are within existing TIFs
etod_lots_tifs = gpd.sjoin(etod_lots, 
                        tif_districts_gdf, 
                        predicate="within")
etod_lots_tifs = etod_lots_tifs.drop_duplicates(subset=["ID"])

# find land that is still available (hasn't been sold)
etod_lots_tifs = etod_lots_tifs.loc[etod_lots_tifs["Property Status"] != "Sold"]
etod_lots_tifs = etod_lots_tifs[["ID", "NAME_right", "Address", "Property Status", 
                                 "Zoning Classification", "geometry"]]
etod_lots_tifs.rename(columns={"NAME_right": "TIF_name",
                               "Zoning Classification": "zoning"}, inplace=True)

#join tif name to l stops
l_stops_gdf = gpd.sjoin(l_stops_gdf.set_geometry("geometry").to_crs(epsg=4326), 
                        tif_districts_gdf, 
                        predicate="within")
l_stops_gdf = l_stops_gdf.drop_duplicates(subset=["STOP_ID"])

#clean up l file
l_stops_gdf = l_stops_gdf[["buffer_half_mile", "STATION_DESCRIPTIVE_NAME", "NAME"]]
l_stops_gdf.rename(columns={"STATION_DESCRIPTIVE_NAME": "station_name",
                                "NAME": "TIF_name"}, inplace=True)

#join tif name to metra stops
metra_stops_gdf = gpd.sjoin(metra_stops_gdf.set_geometry("geometry").to_crs(epsg=4326), 
                        tif_districts_gdf, 
                        predicate="within")
metra_stops_gdf = metra_stops_gdf.drop_duplicates(subset=["STATION_ID"])

#clean up metra file
metra_stops_gdf = metra_stops_gdf[["buffer_half_mile", "NAME_left", "NAME_right"]]
metra_stops_gdf.rename(columns={"NAME_right": "TIF_name",
                                "NAME_left": "station_name"}, inplace=True)

#clean up tif file
tif_districts_gdf = tif_districts_gdf[["NAME", "USE", "the_geom"]]
tif_districts_gdf.rename(columns={"NAME": "TIF_name"}, inplace=True)

#export data for app
tif_districts_gdf.to_file(os.path.join(path, "Data/Processed/tif_districts.shp"))
metra_stops_gdf.to_file(os.path.join(path, "Data/Processed/metra_stops.shp"))
l_stops_gdf.to_file(os.path.join(path, "Data/Processed/l_stops.shp"))
etod_lots_tifs.to_file(os.path.join(path, "Data/Processed/etod_lots_tifs.shp"))