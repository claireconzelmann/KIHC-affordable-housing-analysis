import geopandas as gpd
from shiny import App, ui, render, reactive
import os
import folium
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from branca.element import Element
import pandas as pd

path = os.getcwd()

# Sample geodataframes (replace with actual data)
tif_districts_gdf = gpd.read_file(os.path.join(path, "Data/Processed/tif_districts.shp"))
rail_lines_gdf = gpd.read_file(os.path.join(path, "Data/Processed/rail_lines.shp"))
etod_lots_tifs = gpd.read_file(os.path.join(path, "Data/Processed/etod_lots_tifs.shp"))
bus_routes_gdf = gpd.read_file(os.path.join(path, "Data/Processed/bus_routes.shp"))

app_ui = ui.page_sidebar(
    # Sidebar for layer selection
    ui.sidebar(
        ui.input_checkbox_group(
            "layers",
            "Select layers to display:",
            choices=["TIF Districts", 
                     "Metra and CTA 'L' Lines", 
                     "ETOD Eligible Bus Corridors", 
                     "ETOD Eligible City-Owned Land"],
            selected=["TIF Districts", 
                     "Metra and CTA 'L' Lines", 
                     "ETOD Eligible Bus Corridors", 
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
            ui.output_ui("full_map_plot"),
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
        # If zones are selected, filter the data by selected zones
        if input.zones():
            filtered_df = df[df["zone_cat"].isin(input.zones())]
        else:
            filtered_df = pd.DataFrame()
        return filtered_df
    
    @output
    @render.ui
    def full_map_plot():
        zoned_lots = zone_data()

        # Set default map center (Chicago)
        map_center = [41.8781, -87.6298]

        # Initialize Folium Map
        map_ = folium.Map(location=map_center, zoom_start=11, tiles="CartoDB positron")

        # Plot TIF Districts with tooltips
        if "TIF Districts" in input.layers():
            folium.GeoJson(
                tif_districts_gdf,
                name="TIF Districts",
                style_function=lambda x: {"color": "purple", "weight": 1, "fillOpacity": 0.6},
                tooltip=folium.GeoJsonTooltip(fields=["TIF_name"], aliases=["TIF District:"])  # Tooltip for TIFs
            ).add_to(map_)

        # Plot Metra and CTA 'L' Lines
        if "Metra and CTA 'L' Lines" in input.layers():
            folium.GeoJson(
                rail_lines_gdf.to_crs(epsg=4326),
                name="Metra and CTA 'L' Lines",
                style_function=lambda x: {"color": "limegreen", "weight": 2, "fillOpacity": 0.8}
            ).add_to(map_)

        # Plot ETOD Eligible Bus Corridors
        if "ETOD Eligible Bus Corridors" in input.layers():
            folium.GeoJson(
                bus_routes_gdf.to_crs(epsg=4326),
                name="ETOD Eligible Bus Corridors",
                style_function=lambda x: {"color": "darkgreen", "weight": 2, "fillOpacity": 0.8}
            ).add_to(map_)

        # Plot ETOD Eligible City-Owned Land as skyblue points (No tooltips)
        if "ETOD Eligible City-Owned Land" in input.layers() and not zoned_lots.empty:
            for _, row in zoned_lots.iterrows():
                lat, lon = row.geometry.centroid.y, row.geometry.centroid.x  

                folium.CircleMarker(
                    location=[lat, lon],
                    radius=3,  # Adjust marker size
                    color="skyblue",
                    fill=True,
                    fill_color="skyblue",
                    fill_opacity=0.5
                ).add_to(map_)
        # Add Layer Control
        folium.LayerControl().add_to(map_)

        # Convert Map to HTML
        return ui.HTML(map_._repr_html_())    
    
    @reactive.calc
    def tif_data():
        df = tif_districts_gdf
        return df[df["TIF_name"] == input.tif()]

    @reactive.calc
    def lots_data():
        df = etod_lots_tifs
        filtered_df = df[df["TIF_name"] == input.tif()]

        # Filter based on selected zoning classifications
        if input.zones():
            filtered_df = filtered_df[filtered_df["zone_cat"].isin(input.zones())]

        return filtered_df

    @output
    @render.ui
    def tif_district_plot():
        tif_df = tif_data()
        rail_df = rail_lines_gdf
        bus_df = bus_routes_gdf
        lots_df = lots_data()

        # If there's a selected TIF, update map center to its centroid
        if not tif_df.empty:
            centroid = tif_df.geometry.centroid.unary_union
            map_center = [centroid.y, centroid.x]

        # Initialize Folium map centered at the TIF district
        map_ = folium.Map(location=map_center, zoom_start=14, tiles = "CartoDB positron")
        
        # Add layers based on user selection
        if "TIF Districts" in input.layers():
            folium.GeoJson(
                tif_df.geometry.to_json(),
                style_function=lambda x: {'color': 'purple', 'weight': 1, 'fillOpacity': 0.5}
            ).add_to(map_)
                
        if "Metra and CTA 'L' Lines" in input.layers():
            folium.GeoJson(
                rail_df.to_crs(epsg=4326).geometry.to_json(),
                style_function=lambda x: {'color': 'limegreen', 'weight': 2, 'fillOpacity': 0.6}
            ).add_to(map_)

        if "ETOD Eligible Bus Corridors" in input.layers():
            folium.GeoJson(
                bus_df.to_crs(epsg=4326).geometry.to_json(),
                style_function=lambda x: {'color': 'darkgreen', 'weight': 2, 'fillOpacity': 0.6}
            ).add_to(map_)

        
    # Add ETOD Eligible City-Owned Land with Tooltips
        if "ETOD Eligible City-Owned Land" in input.layers():
            for idx, row in lots_df.iterrows():
                lat, lon = row.geometry.centroid.y, row.geometry.centroid.x  # Get coordinates
                tooltip_text = f"Zoning: {row['zoning']}<br>Address: {row['Address']}<br>Estimated # Units: {row['n_units']}"

                folium.Marker(
                    location=[lat, lon],
                    tooltip=tooltip_text,  # Shows on hover
                    popup=tooltip_text,  # Click to see full details
                    icon=folium.Icon(color="blue", icon="info-sign")
                ).add_to(map_)


        # Define Legend as Raw HTML (Works 100%)
        legend_html = """
        <div style="
            position: fixed;
            bottom: 40px; left: 20px; width: 200px; height: auto;
            background-color: white; z-index:9999; font-size:14px;
            padding: 10px; border-radius: 8px; box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
        ">
            <b>Legend</b><br>
            <i style="background: purple; width: 12px; height: 12px; display: inline-block; border-radius: 2px;"></i> TIF Districts <br>
            <i style="background: limegreen; width: 12px; height: 12px; display: inline-block; border-radius: 2px;"></i> Metra and CTA 'L' Lines <br>
            <i style="background: darkgreen; width: 12px; height: 12px; display: inline-block; border-radius: 2px;"></i> ETOD Eligible Bus Corridors <br>
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