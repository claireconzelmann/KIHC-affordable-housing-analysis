import pandas as pd
import geopandas as gpd
from shapely import wkt
import matplotlib.pyplot as plt
import os
from shapely.geometry import Point
import ast  
import matplotlib.patches as mpatches
import numpy as np

path = os.getcwd()

vacant_buildings = pd.read_csv(os.path.join(path, "Data/Raw/311_Service_Requests_20250330.csv"))
neighborhoods = pd.read_csv(os.path.join(path, "Data/Raw/Neighborhoods.csv"))
sale_buildings = pd.read_csv(os.path.join(path, "Data/Raw/Crexi_Building_Data.csv"))


############################### NEIGHBORHOOD DATA CLEANING ###################################################################

#Creating GDF of neighborhood boundaries in Chicago
neighborhoods["geometry"] = neighborhoods["the_geom"].apply(wkt.loads)
neighborhood_gdf = gpd.GeoDataFrame(neighborhoods, geometry="geometry")
neighborhood_gdf = neighborhood_gdf.set_crs("EPSG:4326", inplace=True)

#Reading assessed home values data
merged_folder = 'Data/merged_gdf_shapefile'
merged_path = os.path.join(path, merged_folder,
 'merged_gdf_shapefile.shp')
merged_gdf = gpd.read_file(merged_path)

#Finding average home values by neighborhood for each Chicago neighborhood
merged_gdf['certified_tot_mean'] = pd.to_numeric(merged_gdf['certifie_1'], errors='coerce').fillna(0)
asessor_2000 = merged_gdf[merged_gdf["year"] == 2000].groupby("pri_neigh")["certified_tot_mean"].mean().reset_index()
asessor_2000 = asessor_2000.rename(columns={"certified_tot_mean": "value_2000"})
    
assessor_2023 = merged_gdf[merged_gdf["year"] == 2023].groupby("pri_neigh")["certified_tot_mean"].mean().reset_index()
assessor_2023 = assessor_2023.rename(columns={"certified_tot_mean": "value_2023"})

#Merging together and creating a difference column
av_merged = pd.merge(asessor_2000, assessor_2023, on="pri_neigh", how="inner")
av_merged["difference"] = abs(av_merged["value_2023"] - av_merged["value_2000"])
av_merged["percent_change"] = (av_merged["difference"] / abs(av_merged["value_2000"]))*100
av_merged = av_merged.rename(columns={'pri_neigh': 'PRI_NEIGH'})

#Merging with neighborhood information to make a GDF with each neighborhood and their level of gentrification 
merged_neighborhoods = pd.merge(av_merged, neighborhood_gdf, on='PRI_NEIGH', how='left')
merged_neighborhoods_gdf = gpd.GeoDataFrame(merged_neighborhoods, geometry='geometry')
merged_neighborhoods_gdf.set_crs('EPSG:4326', allow_override=True, inplace=True)
merged_neighborhoods_gdf = merged_neighborhoods_gdf.rename(columns={'PRI_NEIGH': 'Neigh'})
############################### ADDING SQFT AND ZONING DATA ###################################################################

#Adding parcel addresss and square foot data to merge with vacant building and sales data 
addresses = pd.read_csv(os.path.join(path, "Data/Raw/Assessor_-_Parcel_Addresses_20250403.csv"))
sqft = pd.read_csv(os.path.join(path, "Data/Raw/Assessor_-_Single_and_Multi-Family_Improvement_Characteristics_20250403.csv"))
#grouping by sq ft as some addresses have two observations, for different homes on same property
sqft=sqft.groupby("pin")["building_sqft"].sum().reset_index()
#merging addresses and sqft data and cleaning
addresses_sqft = pd.merge(addresses, sqft, on='pin', how='inner')
addresses_sqft = addresses_sqft.rename(columns={'property_address': 'Address'})
addresses_sqft = addresses_sqft.rename(columns={'building_sqft': 'SqFt'})
addresses_sqft = addresses_sqft[['SqFt', 'Address']]
print(addresses_sqft)

zones = pd.read_csv(os.path.join(path, "Data/Raw/Boundaries_-_Zoning_Districts__current__20250404.csv"))
zones['geometry'] = zones['the_geom'].apply(wkt.loads)
zones_gdf = gpd.GeoDataFrame(zones, geometry="geometry")
zones_gdf.set_crs('EPSG:4326', allow_override=True, inplace=True)

############################### SALES BUILDING DATA CLEANING ###################################################################
#Dropping NAs
sale_buildings = sale_buildings.dropna(subset=['Latitude'])
sale_buildings = sale_buildings.dropna(subset=['Longitude'])

#Filtering
sale_buildings = sale_buildings.loc[sale_buildings["Purchase Entire Building?"]=="Y"]

#merging with square foot data
sale_buildings['Address'] = sale_buildings['Address'].str.upper()

#decided not to merge with square footage data bc have most of info on this
#sale_buildings = pd.merge(sale_buildings, addresses_sqft, on='Address', how='left')

#Creating buildings for sales GDF
sale_buildings_gdf = gpd.GeoDataFrame(sale_buildings, 
                                 geometry=gpd.points_from_xy(sale_buildings.Longitude, 
                                                             sale_buildings.Latitude), 
                                 crs="EPSG:4326")


sale_buildings_gdf = gpd.sjoin(sale_buildings_gdf, zones_gdf,
                             how='left', predicate='within',  lsuffix='_left', rsuffix='_right')

#remove zones that cannot have residential units built
removelist = ["C3", "DS", "M1", "M2", "M3", "PMD", "POS"]
sale_buildings_gdf["flagCol"] = np.where(
    sale_buildings_gdf["ZONE_CLASS"].str.contains('|'.join(removelist)),1,0)
sale_buildings_gdf = sale_buildings_gdf.loc[sale_buildings_gdf["flagCol"] != 1]
sale_buildings_gdf = sale_buildings_gdf.drop(["flagCol"], axis=1)


#create flag for single family zones
sale_buildings_gdf["sfh_flag"] = np.where(sale_buildings_gdf["ZONE_CLASS"].str.contains("RS-"), 1, 0)

#create broader category for zones
zone_cats = {"B-Business":"B", 
             "C-Commercial":"C",
             "D-Downtown": "D",
             "PD-Planned Development":"PD",
             "R-Residential":"R"}

def map_category(item):
    for key, value in zone_cats.items():
        if item.startswith(value):  # Check if item starts with dictionary value
            return key
    return "Unknown"  # Default value if no match is found

sale_buildings_gdf["ZONE_CAT"] = sale_buildings_gdf["ZONE_CLASS"].apply(map_category)

sale_buildings_gdf = sale_buildings_gdf.rename(columns={'PRI_NEIGH': 'Neigh'})
sale_buildings_gdf = sale_buildings_gdf[['Property Name', 'Zoning', 'Asking Price', 'Address', 'SqFt', 'ZONE_CLASS', 'sfh_flag', 'ZONE_CAT', 'geometry']]
############################### VACANT BUILDING DATA CLEANING ###################################################################
#Loading full vacant dataset 
vacant_buildings = vacant_buildings.loc[vacant_buildings["DUPLICATE"]==False]
vacant_buildings = vacant_buildings.rename(columns={'STREET_ADDRESS': 'Address'})
vacant_buildings.drop_duplicates(subset=['Address'])

#merging with address data
vacant_buildings['Address'] = vacant_buildings['Address'].str.upper()
vacant_buildings = pd.merge(vacant_buildings, addresses_sqft, on='Address', how='left')
#creating GDF
vacant_buildings_gdf = gpd.GeoDataFrame(vacant_buildings, geometry=gpd.points_from_xy(vacant_buildings.LONGITUDE, vacant_buildings.LATITUDE), crs="EPSG:4326")


vacant_buildings_gdf = gpd.sjoin(vacant_buildings_gdf, zones_gdf, 
                             how='left', predicate='within', lsuffix='_left', rsuffix='_right')

vacant_buildings_gdf["flagCol"] = np.where(
    vacant_buildings_gdf["ZONE_CLASS"].str.contains('|'.join(removelist)),1,0)
vacant_buildings_gdf = vacant_buildings_gdf.loc[vacant_buildings_gdf["flagCol"] != 1]
vacant_buildings_gdf = vacant_buildings_gdf.drop(["flagCol"], axis=1)

vacant_buildings_gdf["sfh_flag"] = np.where(vacant_buildings_gdf["ZONE_CLASS"].str.contains("RS-"), 1, 0)

vacant_buildings_gdf["ZONE_CAT"] = vacant_buildings_gdf["ZONE_CLASS"].apply(map_category)

vacant_buildings_gdf = vacant_buildings_gdf.rename(columns={'PRI_NEIGH': 'Neigh'})
vacant_buildings_gdf = vacant_buildings_gdf[['Address', 'SR_NUMBER', 'LOCATION', 'SqFt', 'ZONE_CLASS', 'sfh_flag', 'ZONE_CAT', 'geometry']]

##################################### MERGING WITH NEIGHBORHOOD DATA ###########################################################################
vacant_buildings_gdf.drop_duplicates(subset=['LOCATION'], inplace=True)
sale_buildings_gdf.drop_duplicates(subset=['Address'], inplace=True)

#Merging sales and vacant data with neighborhood boundaries 
sale_buildings_neighborhood_gdf = gpd.sjoin(sale_buildings_gdf, merged_neighborhoods_gdf,
                             how='inner', predicate='intersects')

vacant_buildings_neighborhood_gdf = gpd.sjoin(vacant_buildings_gdf, merged_neighborhoods_gdf,
                             how='inner', predicate='intersects')

#Creating a column in neighborhood level dataframe for total square feet available by neighborhood
sale_buildings_neighborhood_gdf_sqft = sale_buildings_neighborhood_gdf[['Neigh', 'SqFt']]
vacant_buildings_neighborhood_gdf_sqft = vacant_buildings_neighborhood_gdf[['Neigh', 'SqFt']]
sqft_neighborhoods = pd.concat([sale_buildings_neighborhood_gdf_sqft, vacant_buildings_neighborhood_gdf_sqft])
sqft_neighborhoods['SqFt'] = pd.to_numeric(sqft_neighborhoods['SqFt'], errors='coerce')
total_sqft_neighborhoods = sqft_neighborhoods.groupby('Neigh')['SqFt'].sum()
merged_neighborhoods_gdf = merged_neighborhoods_gdf.merge(total_sqft_neighborhoods, on='Neigh', how='left')



#export data 
sale_buildings_neighborhood_gdf.to_file(os.path.join(path, "Data/Processed/sale_buildings.shp"))
vacant_buildings_neighborhood_gdf.to_file(os.path.join(path, "Data/Processed/vacant_buildings.shp"))
merged_neighborhoods_gdf.to_file(os.path.join(path, "Data/Processed/neighborhood_level.shp"))


##################################### DATA CHECKING ###########################################################################
n_sale_buildings = sale_buildings_neighborhood_gdf.groupby('Neigh').count().iloc[:, 0]
n_vacant_buildings = vacant_buildings_neighborhood_gdf.groupby('Neigh').count().iloc[:, 0]
no_sqft = vacant_buildings_neighborhood_gdf[vacant_buildings_neighborhood_gdf['SqFt'].isna()]
no_sqft = no_sqft.groupby('Neigh').count().iloc[:, 0]
n_vacant_buildings = pd.merge(n_vacant_buildings, no_sqft, on='Neigh')
n_vacant_buildings['percent_missing'] = n_vacant_buildings['Address_y']/n_vacant_buildings['Address_x']
#Some notes about the data
#36% of vacant building dataset (cleaned) is missing info on square footage data. I originally removed the City Hall observation,
#but there isn't really a way to tell if any of the other calls are "jokes". There are 781 observations in the cleaned data.
#1% of sale buildings dataset (cleaned) is missing info on square footage data. There are 69 observations in the cleaned dataset.
#The top neighborhoods with the greatest percentage change from 2000 and 2023 are Little Italy (163%), Greektown (161%), United Center (161%), Garfield Park (157%), and Chinatown (130%).
#The neighborhoods with the greatest number of total square footage are Garfield Park (745888.0), North Lawndale (568076.0), the Loop (209220.0), Englewood (145940.0), and River North (134235.0). Garfield
#Park has former AllState HQ.
#est. # of units
#paying for more area ratio 


##To do: 
#1. add sqft data to vacant buildings 
####checked data, two other indicators (single vs multi family and type of resident) both wont work
#2. change map color and make percent change - DONE
#3. finish dashboard and add to claire's
#4. calculations for number of units 