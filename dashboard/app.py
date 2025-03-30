import geopandas as gpd
from shiny import App, ui, render, reactive
import os
import folium
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

path = "/Users/claireconzelmann/Documents/GitHub/KIHC-affordable-housing-analysis"

# Sample geodataframes (replace with actual data)
tif_districts_gdf = gpd.read_file(os.path.join(path, "Data/Processed/tif_districts.shp"))
metra_stops_gdf = gpd.read_file(os.path.join(path, "Data/Processed/metra_stops.shp"))
l_stops_gdf = gpd.read_file(os.path.join(path, "Data/Processed/l_stops.shp"))
etod_lots_tifs = gpd.read_file(os.path.join(path, "Data/Processed/etod_lots_tifs.shp"))

app_ui = ui.page_sidebar(
    # Sidebar for layer selection
    ui.sidebar(
        ui.input_checkbox_group(
            "layers",
            "Select layers to display:",
            choices=["TIF Districts", 
                     "Half-Mile Buffer (Metra)", 
                     "Half-Mile Buffer (L Stops)", 
                     "ETOD Eligible City-Owned Land"],
            selected=["TIF Districts", 
                      "Half-Mile Buffer (Metra)",
                      "Half-Mile Buffer (L Stops)", 
                      "ETOD Eligible City-Owned Land"]
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
    @output
    @render.plot
    def full_map_plot():
        fig, ax = plt.subplots()

        # Plot layers based on user selection
        if "TIF Districts" in input.layers():
            tif_districts_gdf.plot(ax=ax, 
                                   color='purple', 
                                   label="TIF Districts",
                                   alpha = 0.8)

        if "Half-Mile Buffer (Metra)" in input.layers():
            metra_stops_gdf.to_crs(epsg=4326).plot(ax=ax, 
                                                   color="pink", 
                                                   alpha=0.8, 
                                                   label="Half-Mile Buffer (Metra)")

        if "Half-Mile Buffer (L Stops)" in input.layers():
            l_stops_gdf.to_crs(epsg=4326).plot(ax=ax, 
                                   color="lightgreen", 
                                   alpha = 0.5,
                                   label="Half-Mile Buffer (L Stops)")

        if "ETOD Eligible City-Owned Land" in input.layers():
            etod_lots_tifs.plot(ax=ax, 
                                color='blue', 
                                markersize=2, 
                                alpha = 0.05,
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
        return df[df["TIF_name"] == input.tif()]

    @output
    @render.ui
    def tif_district_plot():
        tif_df = tif_data()
        metra_df = metra_data()
        l_df = l_data()
        lots_df = lots_data()

        # Initialize Folium map centered at Chicago coordinates
        map_ = folium.Map(location=[41.8781, -87.6298], zoom_start=12)
        
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