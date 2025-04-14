import pandas as pd
import geopandas as gpd
from shapely import wkt
import os
import contextily as ctx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

path = os.getcwd()

sale_buildings_gdf = gpd.read_file(os.path.join(path, "Data/Processed/sale_buildings.shp"))
vacant_buildings_gdf = gpd.read_file(os.path.join(path, "Data/Processed/vacant_buildings.shp"))
merged_neighborhoods_gdf = gpd.read_file(os.path.join(path, "Data/Processed/neighborhood_level.shp"))
neighborhoods = pd.read_csv(os.path.join(path, "Data/Raw/Neighborhoods.csv"))

#Data processing for consistency 
neighborhoods["geometry"] = neighborhoods["the_geom"].apply(wkt.loads)
neighborhood_gdf = gpd.GeoDataFrame(neighborhoods, geometry="geometry")
neighborhood_gdf = neighborhood_gdf.set_crs("EPSG:4326", inplace=True)

#Chicago map by gentrification
fig, ax = plt.subplots(figsize=(10,10))
neighborhood_gdf.dissolve().boundary.to_crs(epsg=3857).plot(ax=ax, 
                                                            color='black',
                                                            linewidth=1, 
                                                            zorder=1)
merged_neighborhoods_gdf.to_crs(epsg=3857).plot(ax=ax, 
                                                column="percent_ch", 
                                                legend_kwds={'label': "Percent Change in Avg. Assessed Value from 2000 to 2023", "orientation": "vertical"},
                                                cmap='Reds', 
                                                legend=True, 
                                                alpha=0.9)
vacant_buildings_gdf.to_crs(epsg=3857).plot(ax=ax, 
                          color='green', 
                          markersize=2,
                          label="Vacant Buildings")
sale_buildings_gdf.to_crs(epsg=3857).plot(ax=ax, 
                          color='black', 
                          markersize=2,
                          label="Buildings for Sale")
legend = [
    mpatches.Patch(color='green', label="Vacant Buildings"),
    mpatches.Patch(color='black', label="Buildings for Sale")]
ax.legend(handles=legend, loc="upper right", fontsize=8)

ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron, alpha=0.5)
ax.set_axis_off()
ax.set_title("Vacant Buildings and Buildings for Sale by Neighborhood Gentrification")

plt.savefig(os.path.join(path, "Maps/Chicago_buildings.png"), dpi=200)
plt.close()

#Subsetting data to Garfield Park
garfield_park_sale = sale_buildings_gdf[sale_buildings_gdf['Neigh'] == 'Garfield Park']
garfield_park_vacant = vacant_buildings_gdf[vacant_buildings_gdf['Neigh'] == 'Garfield Park']
garfield_park = neighborhood_gdf[neighborhood_gdf["PRI_NEIGH"]=="Garfield Park"].to_crs(epsg=3857) 
xmin, ymin, xmax, ymax  = garfield_park.buffer(600).total_bounds

#Garfield park vacant buildings and buildings for sale
fig, ax = plt.subplots(figsize=(10,10))
neighborhood_gdf.to_crs(epsg=3857).plot(ax=ax, 
                                        edgecolor='black',
                                        color='none',
                                        linewidth=2, 
                                        zorder=2)
garfield_park_vacant.to_crs(epsg=3857).plot(ax=ax, 
                          color='green', 
                          markersize=30,
                          label="Vacant Buildings")
garfield_park_sale.to_crs(epsg=3857).plot(ax=ax, 
                          color='black', 
                          markersize=30,
                          label="Buildings for Sale")
legend = [
    mpatches.Patch(color='green', label="Vacant Buildings"),
    mpatches.Patch(color='black', label="Buildings for Sale")]

ax.legend(handles=legend, loc="upper left", fontsize=6)

ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron, alpha=0.5, zoom=15)
ax.set_axis_off()

ax.set_xlim([xmin, xmax])
ax.set_ylim([ymin, ymax])
ax.set_title("Garfield Park: Vacant Buildings and Buildings for Sale")

plt.savefig(os.path.join(path, "Maps/Garfield_park_buildings.png"), dpi=200)
plt.close()
