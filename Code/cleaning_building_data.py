import pandas as pd
import geopandas as gpd
from shapely import wkt
import matplotlib.pyplot as plt
import os
from shapely.geometry import Point
import ast  
import matplotlib.patches as mpatches
import numpy as np

path = '/Users/aliso/OneDrive/Documents/KIHC-affordable-housing-analysis'
vacant_buildings = pd.read_csv(os.path.join(path, "Data/Raw/311_Service_Requests_20250330.csv"))
neighborhoods = pd.read_csv(os.path.join(path, "Data/Raw/Neighborhoods.csv"))
sale_buildings = pd.read_csv(os.path.join(path, "Data/Raw/Crexi_Building_Data.csv"))
unit_area = pd.read_csv(os.path.join(path, "Data/Raw/zone min unit area.csv"))
etod_lots_tifs = gpd.read_file(os.path.join(path, "Data/Processed/etod_lots_tifs.shp"))


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
sale_buildings_gdf = gpd.sjoin(sale_buildings_gdf, merged_neighborhoods_gdf,
                             how='inner', predicate='intersects')

vacant_buildings_gdf = gpd.sjoin(vacant_buildings_gdf, merged_neighborhoods_gdf,
                             how='inner', predicate='intersects')

#Creating a column in neighborhood level dataframe for total square feet available by neighborhood
sale_buildings_gdf_sqft = sale_buildings_gdf[['Neigh', 'SqFt']]
vacant_building_gdf_sqft = vacant_buildings_gdf[['Neigh', 'SqFt']]
sqft_neighborhoods = pd.concat([sale_buildings_gdf_sqft, vacant_building_gdf_sqft])
sqft_neighborhoods['SqFt'] = pd.to_numeric(sqft_neighborhoods['SqFt'], errors='coerce')
total_sqft_neighborhoods = sqft_neighborhoods.groupby('Neigh')['SqFt'].sum()
merged_neighborhoods_gdf = merged_neighborhoods_gdf.merge(total_sqft_neighborhoods, on='Neigh', how='left')



############################### IMPUTING SQUARE FOOT DATA ###################################################################

#using excel sheet to impute missing data for 80 non residential vacant units
missing_vacant_buildings = pd.read_csv(os.path.join(path, "Data/Raw/vacant_building_addresses.csv"))
vacant_buildings_gdf['Calc_Flg']=0
sale_buildings_gdf['Calc_Flg']=0
vacant_buildings_gdf= vacant_buildings_gdf.merge(missing_vacant_buildings[['Address', 'SqFt', 'Calc_Flg']], on='Address', how='left', suffixes=('', '_new'))
vacant_buildings_gdf['SqFt'] = vacant_buildings_gdf['SqFt_new'].combine_first(vacant_buildings_gdf['SqFt'])
vacant_buildings_gdf = vacant_buildings_gdf.drop(columns=['SqFt_new'])
vacant_buildings_gdf['Calc_Flg'] = vacant_buildings_gdf['Calc_Flg_new'].combine_first(vacant_buildings_gdf['Calc_Flg'])
vacant_buildings_gdf = vacant_buildings_gdf.drop(columns=['Calc_Flg_new'])

#using minimum square footage requirement for residential units (RS)
sale_buildings_gdf["SqFt"] = np.where(
    (sale_buildings_gdf["ZONE_CLASS"].isin(["RS-1", "RS-2", "RS-3"])) & 
    (sale_buildings_gdf["SqFt"].isna()),
    1200,  
    sale_buildings_gdf["SqFt"]  #
)

vacant_buildings_gdf["SqFt"] = np.where(
    (vacant_buildings_gdf["ZONE_CLASS"].isin(["RS-1", "RS-2", "RS-3"])) & 
    (vacant_buildings_gdf["SqFt"].isna()),
    1200,  
    vacant_buildings_gdf["SqFt"]  #
)


#using lot square footage for RT and RM units (1690*.8) used 1321 as a unique identifier instead of 1320
sale_buildings_gdf["SqFt"] = np.where(
    (sale_buildings_gdf["ZONE_CLASS"].isin(["RT-4", "RT-3.5", "RT-4A", "RM-5", "RM-6"])) & 
    (sale_buildings_gdf["SqFt"].isna()),
    1321,  
    sale_buildings_gdf["SqFt"]  #
)
sale_buildings_gdf["Calc_Flg"] = np.where(
    sale_buildings_gdf["SqFt"] == 1321,  
    1,  
    sale_buildings_gdf.get('Calc_Flg') 
)

vacant_buildings_gdf["SqFt"] = np.where(
    (vacant_buildings_gdf["ZONE_CLASS"].isin(["RT-4", "RT-3.5", "RT-4A", "RM-5", "RM-6"])) & 
    (vacant_buildings_gdf["SqFt"].isna()),
    1321,  
    vacant_buildings_gdf["SqFt"]  #
)
vacant_buildings_gdf["Calc_Flg"] = np.where(
    vacant_buildings_gdf["SqFt"] == 1321, 
    1,  
    vacant_buildings_gdf.get('Calc_Flg') 
)
##################################### ETOD FLAG ###########################################################################
tif_districts = pd.read_csv(os.path.join(path, "Data/Raw/Boundaries_Tax_Increment_Financing_Districts.csv"))
l_stops = pd.read_csv(os.path.join(path, "Data/Raw/CTA_System_Information_List_of_L_Stops.csv"))
metra_stops_gdf = gpd.read_file(os.path.join(path, "Data/Raw/MetraStations.shp"))
bus_routes_gdf = gpd.read_file(os.path.join(path, "Data/Raw/bus_routes.shp"))
metra_lines_gdf = gpd.read_file(os.path.join(path, "Data/Raw/MetraLinesshp.shp"))
l_lines = pd.read_csv(os.path.join(path, "Data/Raw/CTA_l_lines.csv"))
neighborhoods = pd.read_csv(os.path.join(path, "Data/Raw/Neighborhoods.csv"))

#create geopandas objects
tif_districts["the_geom"] = tif_districts["the_geom"].apply(wkt.loads)
tif_districts_gdf = gpd.GeoDataFrame(tif_districts, geometry="the_geom")
tif_districts_gdf = tif_districts_gdf.set_crs(epsg=4326, inplace=True)

# Convert string representation of tuples of long/lat in lstop data into actual tuples
l_stops["Location"] = l_stops["Location"].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) else x)

l_stops["geometry"] = l_stops["Location"].apply(lambda x: Point(x[1], x[0]))
l_stops_gdf = gpd.GeoDataFrame(l_stops, geometry="geometry")
l_stops_gdf.set_crs(epsg=4326, inplace=True)

bus_routes_gdf.set_crs(epsg=4326, inplace=True)
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

#filter to ETOD eligible bus corridors
etod_corridors = ["55", "63", "79", "9", "X9", "66", "134", "135", 
                  "136", "43", "146", "147", "148", "2", "6", "J14", "26","28",
                  "49", "X49"]
bus_routes_gdf =  bus_routes_gdf.loc[bus_routes_gdf["route"].isin(etod_corridors)]

#create 1/4 mile buffer around bus corridors (ETOD eligible)
bus_routes_gdf = bus_routes_gdf.to_crs(epsg=3857)
bus_routes_gdf["buffer_quarter_mile"] = bus_routes_gdf.geometry.buffer(402.335)
bus_routes_gdf = bus_routes_gdf.to_crs(epsg=4326)

#find vacant buildings within 1/2 buffers of transit stations
vacant_buildings_gdf = vacant_buildings_gdf.rename(columns={'index_right': 'index_right_renamed'}, errors='ignore')

etod_lots_l = gpd.sjoin(vacant_buildings_gdf, 
                        l_stops_gdf.set_geometry("buffer_half_mile").to_crs(epsg=4326), 
                        predicate="within")

etod_lots_metra = gpd.sjoin(vacant_buildings_gdf, 
                        metra_stops_gdf.set_geometry("buffer_half_mile").to_crs(epsg=4326), 
                        predicate="within")

#find vacant buildings within 1/4 mile buffers of bus corridors
etod_lots_bus = gpd.sjoin(vacant_buildings_gdf, 
                        bus_routes_gdf.set_geometry("buffer_quarter_mile").to_crs(epsg=4326), 
                        predicate="within")

etod_lots = pd.concat([etod_lots_l, etod_lots_metra, etod_lots_bus], 
                      ignore_index=True).drop_duplicates(subset=["Address"])
etod_lots = etod_lots.drop("index_right", axis=1)

#find etod eligible buildings that are within existing TIFs
etod_lots_tifs = gpd.sjoin(etod_lots, 
                        tif_districts_gdf, 
                        predicate="within")
etod_lots_tifs = etod_lots_tifs.drop_duplicates(subset=["Address"])
etod_lots_tifs = etod_lots_tifs[['Address', 'geometry']]

# merging list of ETOD eligible buildings with larger dataset
vacant_buildings_gdf = gpd.sjoin(vacant_buildings_gdf, etod_lots_tifs, how="left", predicate="intersects")
#creating indicator and dropping ETOD variables
vacant_buildings_gdf['ETOD_ADU_eligible'] = np.where(vacant_buildings_gdf["Address_right"].isna(),
                                  0, 1)
vacant_buildings_gdf = vacant_buildings_gdf.drop(columns=['Address_right', 'index_right'])

vacant_buildings_gdf = vacant_buildings_gdf.rename(columns={"Address_left": "Address"})

##################################### ADU FLAG ###########################################################################
#reading in info about ADUs
adu_districts = pd.read_csv(os.path.join(path, "Data/Raw/Additional_Dwelling_Unit_Areas_20250408.csv"))
#creating gdf
adu_districts["the_geom"] = adu_districts["the_geom"].apply(wkt.loads)
adu_districts_gdf = gpd.GeoDataFrame(adu_districts, geometry="the_geom")
adu_districts_gdf = adu_districts_gdf.set_crs(epsg=4326, inplace=True)
#merging with vacant buildings data
vacant_buildings_gdf = gpd.sjoin(vacant_buildings_gdf, adu_districts_gdf, how="left", predicate="intersects")
#creating a flag for units in ADU eligible areas
vacant_buildings_gdf['ETOD_ADU_eligible'] = np.where(vacant_buildings_gdf["index_right"].isna(),
                                  vacant_buildings_gdf['ETOD_ADU_eligible'], 1)
##################################### CHANGING ZONING ###########################################################################
#renaming
sale_buildings_gdf = sale_buildings_gdf.rename(columns={"ZONE_CLASS": "zoning"})
vacant_buildings_gdf = vacant_buildings_gdf.rename(columns={"ZONE_CLASS": "zoning"})

#cleaning square feet variable 
sale_buildings_gdf['SqFt'] = sale_buildings_gdf['SqFt'].astype(str)
vacant_buildings_gdf['SqFt'] = vacant_buildings_gdf['SqFt'].astype(str)

sale_buildings_gdf['SqFt'] = pd.to_numeric(sale_buildings_gdf['SqFt'].str.replace(',', ''), errors='coerce')
sale_buildings_gdf['SqFt'] = sale_buildings_gdf['SqFt'].fillna(0.0).astype(int)
sale_buildings_gdf.replace({"SqFt": 0.0}, np.nan, inplace=True)

vacant_buildings_gdf['SqFt'] = pd.to_numeric(vacant_buildings_gdf['SqFt'].str.replace(',', ''), errors='coerce')
vacant_buildings_gdf['SqFt'] = vacant_buildings_gdf['SqFt'].fillna(0.0).astype(int)
vacant_buildings_gdf.replace({"SqFt": 0.0}, np.nan, inplace=True)


#merging with unit area data
sale_buildings_gdf = pd.merge(sale_buildings_gdf, unit_area, on="zoning", how="left")
vacant_buildings_gdf = pd.merge(vacant_buildings_gdf, unit_area, on="zoning", how="left")

sale_buildings_gdf = sale_buildings_gdf.rename(columns={"ZONE_CAT": "original_zoning_cat"})
vacant_buildings_gdf = vacant_buildings_gdf.rename(columns={"ZONE_CAT": "original_zoning_cat"})
sale_buildings_gdf = sale_buildings_gdf.rename(columns={"zoning": "original_zoning"})
vacant_buildings_gdf = vacant_buildings_gdf.rename(columns={"zoning": "original_zoning"})

#changing PD to BS-3
sale_buildings_gdf["zoning"] = np.where(sale_buildings_gdf["original_zoning"].str.startswith("PD"),
                                  "B1-3", sale_buildings_gdf["original_zoning"])
sale_buildings_gdf["zone_cat"] = np.where(sale_buildings_gdf["original_zoning_cat"]=="PD-Planned Development",
                                  "B-Business", sale_buildings_gdf["original_zoning_cat"])
vacant_buildings_gdf["zoning"] = np.where(vacant_buildings_gdf["original_zoning"].str.startswith("PD"),
                                  "B1-3", vacant_buildings_gdf["original_zoning"])
vacant_buildings_gdf["zone_cat"] = np.where(vacant_buildings_gdf["original_zoning_cat"]=="PD-Planned Development",
                                  "B-Business", vacant_buildings_gdf["original_zoning_cat"])
#changing RS to RT in ETOD lots
vacant_buildings_gdf["zoning"] = np.where(
    (vacant_buildings_gdf["original_zoning"].isin(["RS-1", "RS-2", "RS-3"])) & 
    (vacant_buildings_gdf["ETOD_ADU_eligible"]==1),
    "RT-4", vacant_buildings_gdf["zoning"])

# change FAR for B-3/C-3 zones based on Connected Communities                                         
sale_buildings_gdf["FAR"] = np.where(sale_buildings_gdf["zoning"].isin(["B1-3", "B2-3", "B3-3", "C1-3", "C2-3", "C3-3"]),
                                  4, sale_buildings_gdf["FAR"])
vacant_buildings_gdf["FAR"] = np.where(vacant_buildings_gdf["zoning"].isin(["B1-3", "B2-3", "B3-3", "C1-3", "C2-3", "C3-3"]),
                                  4, vacant_buildings_gdf["FAR"])

#for lots where i calculate the sq footage based off of land square footage, calculate square feet using FAR
sale_buildings_gdf["sq_ft"] = np.where((sale_buildings_gdf["Calc_Flg"] == 1),  
                                       sale_buildings_gdf["SqFt"]*sale_buildings_gdf["FAR"],
                                       sale_buildings_gdf["SqFt"])

vacant_buildings_gdf["sq_ft"] = np.where((vacant_buildings_gdf["Calc_Flg"] == 1),  
                                       vacant_buildings_gdf["SqFt"]*vacant_buildings_gdf["FAR"],
                                       vacant_buildings_gdf["SqFt"])

vacant_buildings_gdf["sq_ft"] = np.where(
    (vacant_buildings_gdf["original_zoning"].isin(["RS-1", "RS-2", "RS-3"])) & 
    (vacant_buildings_gdf["ETOD_ADU_eligible"]==1),
    vacant_buildings_gdf["sq_ft"]*1.2, vacant_buildings_gdf["sq_ft"])


#for non residential zoned lots, calculate sq footage above ground floor
sale_buildings_gdf["sq_ft_residential"] = np.where((sale_buildings_gdf["zone_cat"]=="B-Business") |
                                               (sale_buildings_gdf["zone_cat"]=="C-Commercial"),
                                               sale_buildings_gdf["sq_ft"]*.75, 
                                               sale_buildings_gdf["sq_ft"])
vacant_buildings_gdf["sq_ft_residential"] = np.where((vacant_buildings_gdf["zone_cat"]=="B-Business") |
                                               (vacant_buildings_gdf["zone_cat"]=="C-Commercial"), 
                                               vacant_buildings_gdf["sq_ft"]*.75, 
                                               vacant_buildings_gdf["sq_ft"])


#assume 720 sq. ft. average unit size unless min unit size is larger
sale_buildings_gdf["avg_unit_size"] = np.where(sale_buildings_gdf["lot_area_per_unit"] > 720, 
                                           sale_buildings_gdf["lot_area_per_unit"], 720)


#assume 720 sq. ft. average unit size unless min unit size is larger
vacant_buildings_gdf["avg_unit_size"] = np.where(vacant_buildings_gdf["lot_area_per_unit"] > 720, 
                                           vacant_buildings_gdf["lot_area_per_unit"], 720)

# calculate estimate of number of units per lot
# 0 units if residential eligible sq ft is smaller than minimum unit size
sale_buildings_gdf["n_units"] = np.where(sale_buildings_gdf["avg_unit_size"] > sale_buildings_gdf["sq_ft_residential"], 0, np.nan)

# divide residential eligible sq ft by average unit size for all others and round down
sale_buildings_gdf["n_units"] = np.where(sale_buildings_gdf["n_units"].isna(), 
                                     np.floor(sale_buildings_gdf["sq_ft_residential"]/sale_buildings_gdf["avg_unit_size"]), 
                                     sale_buildings_gdf["n_units"])

# 1 unit for single family
sale_buildings_gdf["n_units"] = np.where(sale_buildings_gdf["zoning"].isin(["RS-1", "RS-2", "RS-3"]), 1, sale_buildings_gdf["n_units"])

# calculate estimate of number of units per lot
# 0 units if residential eligible sq ft is smaller than minimum unit size
vacant_buildings_gdf["n_units"] = np.where(vacant_buildings_gdf["avg_unit_size"] > vacant_buildings_gdf["sq_ft_residential"], 0, np.nan)

# divide residential eligible sq ft by average unit size for all others and round down
vacant_buildings_gdf["n_units"] = np.where(vacant_buildings_gdf["n_units"].isna(), 
                                     np.floor(vacant_buildings_gdf["sq_ft_residential"]/vacant_buildings_gdf["avg_unit_size"]), 
                                     vacant_buildings_gdf["n_units"])

# 1 unit for single family
vacant_buildings_gdf["n_units"] = np.where(vacant_buildings_gdf["zoning"].isin(["RS-1", "RS-2", "RS-3"]), 1, vacant_buildings_gdf["n_units"])

print(sale_buildings_gdf["n_units"].sum(skipna=True))
print(vacant_buildings_gdf["n_units"].sum(skipna=True))
print(sale_buildings_gdf["n_units"].sum(skipna=True)+vacant_buildings_gdf["n_units"].sum(skipna=True))


############################### SAVING DATA ###################################################################
vacant_buildings_gdf.to_file(os.path.join(path, "Data/Processed/vacant_buildings.shp"))
sale_buildings_gdf.to_file(os.path.join(path, "Data/Processed/sale_buildings.shp"))
merged_neighborhoods_gdf.to_file(os.path.join(path, "Data/Processed/neighborhood_level.shp"))