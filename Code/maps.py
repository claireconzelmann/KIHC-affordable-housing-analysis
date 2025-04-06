import pandas as pd
import geopandas as gpd
from shapely import wkt
import os
import contextily as ctx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from shapely.ops import unary_union, linemerge

path = os.getcwd()

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

# keep unique sections of rail lines
all_geometries = l_lines_gdf.geometry.tolist() + metra_lines_chi_gdf.geometry.tolist()

# Merge all rail lines into a single unified geometry
merged_lines = linemerge(unary_union(all_geometries))
unique_lines = list(merged_lines.geoms)
rail_gdf_unique = gpd.GeoDataFrame(geometry=unique_lines, crs=l_lines_gdf.crs)

merged_lines_bus = linemerge(unary_union(bus_routes_gdf.geometry))
# Convert back to individual unique LineStrings
unique_lines_bus = list(merged_lines_bus.geoms) 
bus_gdf_unique = gpd.GeoDataFrame(geometry=unique_lines_bus, crs=bus_routes_gdf.crs)
'''
#plot ETOD eligible lots in all of Chicago
fig, ax = plt.subplots(figsize=(10,10))
neighborhood_gdf.dissolve().boundary.to_crs(epsg=3857).plot(ax=ax, 
                                                            color='black',
                                                            linewidth=1, 
                                                            alpha=0.2,
                                                            zorder=1)
tif_districts_gdf.to_crs(epsg=3857).plot(ax=ax, 
                       color='purple',
                       label="TIF districts",
                       alpha =0.6,
                       zorder = 2)
rail_gdf_unique.to_crs(epsg=3857).plot(ax=ax, 
                         color="limegreen", 
                         alpha=0.6,
                         zorder = 3)

bus_gdf_unique.to_crs(epsg=3857).plot(ax=ax, 
                         color="darkgreen", 
                         label="bus",
                         alpha=0.6,
                         zorder = 3)
etod_lots_tifs.to_crs(epsg=3857).plot(ax=ax, 
                    color='skyblue', 
                    markersize=1.5,
                    zorder = 5)

legend_patches = [
    mpatches.Patch(color='purple', label="TIF Districts", alpha=0.6),
    mpatches.Patch(color='limegreen', label="Metra and CTA 'L' Lines", alpha=0.6),
    mpatches.Patch(color='darkgreen', label="Eligible Bus Corridors", alpha=0.6),
    mpatches.Patch(color='skyblue', label="ETOD Eligible City Owned Vacant Lots")
]
ax.legend(handles=legend_patches, loc="upper right", fontsize=8)

ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron, alpha=0.5)
ax.set_axis_off()
ax.set_title("ETOD Eligible City Owned Vacant Lots in TIF Districts")

plt.savefig(os.path.join(path, "Maps/ETOD_vacant_lots.png"), dpi=300)
plt.close()
'''
# plot zoomed in version of ETOD eligible plots focusing on Englewood
englewood = neighborhood_gdf.loc[neighborhood_gdf["SEC_NEIGH"]=="ENGLEWOOD"]
bounding_box = englewood.to_crs(epsg=3857) 

#clip tif disctricts by englewood
englewood_tif = gpd.clip(tif_districts_gdf, englewood)

# Get bounding box from the polygon
xmin, ymin, xmax, ymax  = bounding_box.buffer(600).total_bounds

fig, ax = plt.subplots(figsize=(10,10))
neighborhood_gdf.to_crs(epsg=3857).plot(ax=ax, 
                                        edgecolor='black',
                                        color='none',
                                        linewidth=2,
                                        alpha =0.1, 
                                        zorder=3)
tif_districts_gdf.to_crs(epsg=3857).plot(ax=ax, 
                       color='purple',
                       label="TIF districts",
                       alpha=0.5,
                       zorder = 1)
englewood_tif.to_crs(epsg=3857).plot(ax=ax, 
                       color='purple',
                       zorder = 2)
englewood.to_crs(epsg=3857).plot(ax=ax, 
                                edgecolor='black',
                                color='none',
                                linewidth=2, 
                                zorder=4)
rail_gdf_unique.to_crs(epsg=3857).plot(ax=ax, 
                         color="limegreen", 
                         alpha=0.6,
                         zorder = 5)

bus_gdf_unique.to_crs(epsg=3857).plot(ax=ax, 
                         color="darkgreen", 
                         label="bus",
                         alpha=0.6,
                         zorder = 6)

etod_lots_tifs.to_crs(epsg=3857).plot(ax=ax, 
                    color='skyblue', 
                    markersize=4,
                    zorder = 7)

legend_patches = [
    mpatches.Patch(color='purple', label="TIF Districts"),
    mpatches.Patch(color='limegreen', label="Metra and CTA 'L' Lines", alpha=0.6),
    mpatches.Patch(color='darkgreen', label="Eligible Bus Corridors", alpha=0.6),
    mpatches.Patch(color='skyblue', label="ETOD Eligible City Owned Vacant Lots"),
    mpatches.Patch(facecolor='none', edgecolor='black', label="Community Area Boundary")
]

legend = ax.legend(handles=legend_patches, loc="upper left", framealpha=1, fontsize=8)
legend.get_frame().set_facecolor('white')
legend.get_frame().set_alpha(1) 

ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron, alpha=0.5, zoom=15)
ax.set_axis_off()

ax.set_xlim([xmin, xmax])
ax.set_ylim([ymin, ymax])
ax.set_title("Englewood: ETOD Eligible City Owned Vacant Lots in TIF Districts")

plt.savefig(os.path.join(path, "Maps/englewood_ETOD_vacant_lots.png"), dpi=300)
plt.close()


