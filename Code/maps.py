import pandas as pd
import geopandas as gpd
from shapely import wkt
import os
import contextily as ctx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

path = "/Users/claireconzelmann/Documents/GitHub/KIHC-affordable-housing-analysis"
tif_districts_gdf = gpd.read_file(os.path.join(path, "Data/Processed/tif_districts.shp"))
metra_lines_gdf = gpd.read_file(os.path.join(path, "Data/Raw/MetraLinesshp.shp"))
l_lines = pd.read_csv(os.path.join(path, "Data/Raw/CTA_l_lines.csv"))
bus_routes_gdf = gpd.read_file(os.path.join(path, "Data/Processed/bus_routes.shp"))
etod_lots_tifs = gpd.read_file(os.path.join(path, "Data/Processed/etod_lots_tifs.shp"))
neighborhoods = pd.read_csv(os.path.join(path, "Data/Raw/Neighborhoods.csv"))

#initial data processing steps
neighborhoods["geometry"] = neighborhoods["the_geom"].apply(wkt.loads)
neighborhood_gdf = gpd.GeoDataFrame(neighborhoods, geometry="geometry")
neighborhood_gdf = neighborhood_gdf.set_crs("EPSG:4326", inplace=True)

#convert to geopandas and set coordinate system
l_lines["the_geom"] = l_lines["the_geom"].apply(wkt.loads)
l_lines_gdf = gpd.GeoDataFrame(l_lines, geometry="the_geom")
l_lines_gdf = l_lines_gdf.set_crs(epsg=4326, inplace=True)

metra_lines_gdf.to_crs(epsg=4326, inplace=True)

#clip metra lines to chicago extent
metra_lines_chi_gdf = gpd.clip(metra_lines_gdf, neighborhood_gdf)

#plot ETOD eligible lots in all of Chicago
fig, ax = plt.subplots(figsize=(10,10))
neighborhood_gdf.dissolve().boundary.to_crs(epsg=3857).plot(ax=ax, 
                                                            color='black',
                                                            linewidth=1, 
                                                            zorder=1)
tif_districts_gdf.to_crs(epsg=3857).plot(ax=ax, 
                       color='purple',
                       label="TIF districts",
                       zorder = 2)
metra_lines_chi_gdf.to_crs(epsg=3857).plot(ax=ax, 
                         color="red", 
                         alpha=0.5,
                         zorder = 3)
bus_routes_gdf.to_crs(epsg=3857).plot(ax=ax, 
                         color="green", 
                         label="bus",
                         alpha=0.1,
                         zorder = 3)
l_lines_gdf.to_crs(epsg=3857).plot(ax=ax, 
                 color="red", 
                 alpha=0.5,
                 zorder = 4)
etod_lots_tifs.to_crs(epsg=3857).plot(ax=ax, 
                    color='skyblue', 
                    markersize=2,
                    zorder = 5)

legend_patches = [
    mpatches.Patch(color='purple', label="TIF Districts"),
    mpatches.Patch(color='red', label="Metra and CTA 'L' Lines"),
    mpatches.Patch(color='green', label="Eligible Bus Corridors"),
    mpatches.Patch(color='skyblue', label="City Owned Vacant Lots")
]
ax.legend(handles=legend_patches, loc="upper right", fontsize=8)

ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron, alpha=0.5)
ax.set_axis_off()
ax.set_title("ETOD Eligible City Owned Vacant Lots in TIF Districts")

plt.savefig(os.path.join(path, "Maps/ETOD_vacant_lots.png"), dpi=200)
plt.close()

# plot zoomed in version of ETOD eligible plots focusing on Englewood
bounding_box = neighborhood_gdf.loc[
    neighborhood_gdf["SEC_NEIGH"]=="ENGLEWOOD"].to_crs(epsg=3857) 

# Get bounding box from the polygon
xmin, ymin, xmax, ymax  = bounding_box.buffer(600).total_bounds

fig, ax = plt.subplots(figsize=(10,10))
neighborhood_gdf.to_crs(epsg=3857).plot(ax=ax, 
                                        edgecolor='black',
                                        color='none',
                                        linewidth=2, 
                                        zorder=2)
tif_districts_gdf.to_crs(epsg=3857).plot(ax=ax, 
                       color='purple',
                       label="TIF districts",
                       zorder = 1)

metra_lines_chi_gdf.to_crs(epsg=3857).plot(ax=ax, 
                         color="red", 
                         alpha=0.5,
                         zorder = 3,
                         linewidth=2)
bus_routes_gdf.to_crs(epsg=3857).plot(ax=ax, 
                         color="green", 
                         label="bus",
                         alpha=0.1,
                         zorder = 3,
                         linewidth=2)
l_lines_gdf.to_crs(epsg=3857).plot(ax=ax, 
                 color="red", 
                 alpha=0.5,
                 zorder = 4,
                 linewidth=2)
etod_lots_tifs.to_crs(epsg=3857).plot(ax=ax, 
                    color='skyblue', 
                    markersize=4,
                    zorder = 5)

legend_patches = [
    mpatches.Patch(color='purple', label="TIF Districts"),
    mpatches.Patch(color='red', label="Metra and CTA 'L' Lines"),
    mpatches.Patch(color='green', label="Eligible Bus Corridors"),
    mpatches.Patch(color='skyblue', label="City Owned Vacant Lots"),
    mpatches.Patch(facecolor='none', edgecolor='black', label="Community Area Boundary")
]
ax.legend(handles=legend_patches, loc="upper left", fontsize=8)

ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron)
ax.set_axis_off()

ax.set_xlim([xmin, xmax])
ax.set_ylim([ymin, ymax])
ax.set_title("Englewood: ETOD Eligible City Owned Vacant Lots in TIF Districts")

plt.savefig(os.path.join(path, "Maps/englewood_ETOD_vacant_lots.png"), dpi=200)
plt.close()


