import geopandas as gpd
from shiny import App, ui, render, reactive
import os
import folium
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from branca.element import Element

path = os.getcwd()

# Sample geodataframes (replace with actual data)
tif_districts_gdf = gpd.read_file(os.path.join(path, "Data/Processed/tif_districts.shp"))
metra_stops_gdf = gpd.read_file(os.path.join(path, "Data/Processed/metra_stops.shp"))
l_stops_gdf = gpd.read_file(os.path.join(path, "Data/Processed/l_stops.shp"))
etod_lots_tifs = gpd.read_file(os.path.join(path, "Data/Processed/etod_lots_tifs.shp"))
bus_routes_gdf = gpd.read_file(os.path.join(path, "Data/Processed/bus_routes.shp"))

#drop duplicates created when spatially joining TIF name to transit data if stop/route is in multiple TIFs
bus_routes_nodup = bus_routes_gdf.drop_duplicates(subset=["route"])
l_stops_nodup = l_stops_gdf.drop_duplicates(subset=["STOP_ID"])
metra_stops_nodup = metra_stops_gdf.drop_duplicates(subset=["STATION_ID"])

app_ui = ui.page_sidebar(
    # Sidebar for layer selection
    ui.sidebar(
        ui.input_checkbox_group(
            "layers",
            "Select layers to display:",
            choices=["TIF Districts", 
                     "Half-Mile Buffer (Metra)", 
                     "Half-Mile Buffer (L Stops)",
                     "Quarter-Mile Buffer (Bus Corridors)", 
                     "ETOD Eligible City-Owned Land"],
            selected=["TIF Districts", 
                      "Half-Mile Buffer (Metra)",
                      "Half-Mile Buffer (L Stops)", 
                      "Quarter-Mile Buffer (Bus Corridors)",
                      "ETOD Eligible City-Owned Land"]
        ),
        ui.input_checkbox_group(
            "zones",
            "Filter by zoning classification:",
            choices=["B-Business",
                     "C-Commercial",
                     "D-Downtown",
                     "PD-Planned Development",
                     "R-Residential"],
            selected=["B-Business",
                     "C-Commercial",
                     "D-Downtown",
                     "PD-Planned Development",
                     "R-Residential"]
        )

    ),

    # Main content layout with two columns
    ui.layout_columns(
        # First Column: Map Display
        ui.card(
            ui.output_plot("full_map_plot"),
            full_screen=True,
        ),
        
        # Second Column: TIF District Selection and Plot
        ui.card(
            ui.input_select(id="tif", label="Choose a TIF District:", choices=[]),
            ui.output_ui("tif_district_plot"),
            full_screen=True,
        ),
    )
)

# Server
def server(input, output, session):

    @reactive.calc
    def zone_data():
        df = etod_lots_tifs
        # Filter based on selected zoning classifications
        if input.zones():
            filtered_df = df[df["zone_cat"].isin(input.zones())]

        return filtered_df
    
    @output
    @render.plot
    def full_map_plot():
        zoned_lots = zone_data()

        fig, ax = plt.subplots()

        # Plot layers based on user selection
        if "TIF Districts" in input.layers():
            tif_districts_gdf.plot(ax=ax, 
                                   color='purple', 
                                   label="TIF Districts",
                                   alpha = 0.8)

        if "Half-Mile Buffer (Metra)" in input.layers():
            metra_stops_nodup.to_crs(epsg=4326).plot(ax=ax, 
                                                   color="pink", 
                                                   alpha=0.8, 
                                                   label="Half-Mile Buffer (Metra)")

        if "Half-Mile Buffer (L Stops)" in input.layers():
            l_stops_nodup.to_crs(epsg=4326).plot(ax=ax, 
                                   color="lightgreen", 
                                   alpha = 0.5,
                                   label="Half-Mile Buffer (L Stops)")
            
        if "Quarter-Mile Buffer (Bus Corridors)" in input.layers():
            bus_routes_nodup.to_crs(epsg=4326).plot(ax=ax, 
                                   color="orange", 
                                   alpha = 0.5,
                                   label="Quarter-Mile Buffer (Bus Corridors)")

        if "ETOD Eligible City-Owned Land" in input.layers():
            zoned_lots.plot(ax=ax, 
                                color='blue', 
                                markersize=2, 
                                alpha = 0.5,
                                label="ETOD Eligible City-Owned Land")

        # Add legend
        legend_patches = []
        if "TIF Districts" in input.layers():
            legend_patches.append(mpatches.Patch(color='purple', 
                                                 label="TIF Districts"))
            
        if "Half-Mile Buffer (Metra)" in input.layers():
            legend_patches.append(mpatches.Patch(color='pink', 
                                                 label="Half-Mile Buffer (Metra)"))
            
        if "Half-Mile Buffer (L Stops)" in input.layers():
            legend_patches.append(mpatches.Patch(color='lightgreen', 
                                                 label="Half-Mile Buffer (L Stops)"))
        
        if "Quarter-Mile Buffer (Bus Corridors)" in input.layers():
            legend_patches.append(mpatches.Patch(color='orange', 
                                                 label="Quarter-Mile Buffer (Bus Corridors)"))
            
        if "ETOD Eligible City-Owned Land" in input.layers():
            legend_patches.append(mpatches.Patch(color='blue', 
                                                 label="ETOD Eligible City-Owned Land"))

        if legend_patches:
            ax.legend(handles=legend_patches, loc="lower left", fontsize=5, framealpha=0)
    
        return fig
    
    @reactive.calc
    def tif_data():
        df = tif_districts_gdf
        return df[df["TIF_name"] == input.tif()]

    @reactive.calc
    def metra_data():
        df = metra_stops_gdf
        return df[df["TIF_name"] == input.tif()]

    @reactive.calc
    def l_data():
        df = l_stops_gdf
        return df[df["TIF_name"] == input.tif()]

    @reactive.calc
    def lots_data():
        df = etod_lots_tifs
        filtered_df = df[df["TIF_name"] == input.tif()]

        # Filter based on selected zoning classifications
        if input.zones():
            filtered_df = filtered_df[filtered_df["zone_cat"].isin(input.zones())]

        return filtered_df
    
    @reactive.calc
    def bus_data():
        df = bus_routes_gdf
        return df[df["TIF_name"] == input.tif()]

    @output
    @render.ui
    def tif_district_plot():
        tif_df = tif_data()
        metra_df = metra_data()
        l_df = l_data()
        bus_df = bus_data()
        lots_df = lots_data()

        # If there's a selected TIF, update map center to its centroid
        if not tif_df.empty:
            centroid = tif_df.geometry.centroid.unary_union
            map_center = [centroid.y, centroid.x]

        # Initialize Folium map centered at the TIF district
        map_ = folium.Map(location=map_center, zoom_start=14)
        
        # Add layers based on user selection
        if "TIF Districts" in input.layers():
            folium.GeoJson(
                tif_df.geometry.to_json(),
                style_function=lambda x: {'color': 'purple', 'weight': 1, 'fillOpacity': 0.5}
            ).add_to(map_)
        
        if "Half-Mile Buffer (Metra)" in input.layers():
            folium.GeoJson(
                metra_df.to_crs(epsg=4326).geometry.to_json(),  # Half-mile buffer
                style_function=lambda x: {'color': 'pink', 'weight': 1, 'fillOpacity': 0.5}
            ).add_to(map_)
        
        if "Half-Mile Buffer (L Stops)" in input.layers():
            folium.GeoJson(
                l_df.to_crs(epsg=4326).geometry.to_json(),  # Half-mile buffer
                style_function=lambda x: {'color': 'lightgreen', 'weight': 1, 'fillOpacity': 0.5}
            ).add_to(map_)

        if "Quarter-Mile Buffer (Bus Corridors)" in input.layers():
            folium.GeoJson(
                bus_df.to_crs(epsg=4326).geometry.to_json(),  # quarter-mile buffer
                style_function=lambda x: {'color': 'orange', 'weight': 1, 'fillOpacity': 0.5}
            ).add_to(map_)

        
    # Add ETOD Eligible City-Owned Land with Tooltips
        if "ETOD Eligible City-Owned Land" in input.layers():
            for idx, row in lots_df.iterrows():
                lat, lon = row.geometry.centroid.y, row.geometry.centroid.x  # Get coordinates
                tooltip_text = f"Zoning: {row['zoning']}<br>Address: {row['Address']}"

                folium.Marker(
                    location=[lat, lon],
                    tooltip=tooltip_text,  # Shows on hover
                    popup=tooltip_text,  # Click to see full details
                    icon=folium.Icon(color="blue", icon="info-sign")
                ).add_to(map_)


        # 🔹 Define Legend as Raw HTML (Works 100%)
        legend_html = """
        <div style="
            position: fixed;
            bottom: 40px; left: 20px; width: 200px; height: auto;
            background-color: white; z-index:9999; font-size:14px;
            padding: 10px; border-radius: 8px; box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
        ">
            <b>Legend</b><br>
            <i style="background: purple; width: 12px; height: 12px; display: inline-block; border-radius: 2px;"></i> TIF Districts <br>
            <i style="background: pink; width: 12px; height: 12px; display: inline-block; border-radius: 2px;"></i> Half-Mile Buffer (Metra) <br>
            <i style="background: lightgreen; width: 12px; height: 12px; display: inline-block; border-radius: 2px;"></i> Half-Mile Buffer (L Stops) <br>
            <i style="background: orange; width: 12px; height: 12px; display: inline-block; border-radius: 2px;"></i> Quarter-Mile Buffer (Bus Corridors) <br>
            <i style="background: skyblue; width: 12px; height: 12px; display: inline-block; border-radius: 2px;"></i> ETOD Eligible Land <br>
        </div>
        """

        # 🔹 Use `Element` instead of MacroElement
        legend = Element(legend_html)
        map_.get_root().html.add_child(legend)

       # Return the HTML representation of the map
        map_html = map_._repr_html_()  # This gets the HTML representation of the map
        
        # Use ui.html to embed the map directly into the UI
        return ui.HTML(map_html)
        
    @reactive.effect
    def _():
        tif_list = etod_lots_tifs["TIF_name"].unique().tolist()
        tif_list = sorted(tif_list)
        ui.update_select("tif", choices=tif_list)

# Run the app
app = App(app_ui, server)