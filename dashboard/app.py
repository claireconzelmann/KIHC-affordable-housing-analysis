import geopandas as gpd
from shiny import App, ui, render, reactive
import os
import folium
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import branca
from branca.element import Element
import pandas as pd

path = os.getcwd()

tif_districts_gdf = gpd.read_file(os.path.join(path, "Data/Processed/tif_districts.shp"))
rail_lines_gdf = gpd.read_file(os.path.join(path, "Data/Processed/rail_lines.shp"))
etod_lots_tifs = gpd.read_file(os.path.join(path, "Data/Processed/etod_lots_tifs.shp"))
bus_routes_gdf = gpd.read_file(os.path.join(path, "Data/Processed/bus_routes.shp"))
sale_buildings_gdf = gpd.read_file(os.path.join(path, "Data/Processed/sale_buildings.shp"))
vacant_buildings_gdf = gpd.read_file(os.path.join(path, "Data/Processed/vacant_buildings.shp"))
merged_neighborhoods_gdf = gpd.read_file(os.path.join(path, "Data/Processed/neighborhood_level.shp"))


app_ui_page1 = ui.page_sidebar(
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
        ),
        ui.div(
            ui.markdown("These analyses were conducted as part of a proposal for the 2025 Kreisman Initiative Housing Challenge. Team members: Claire Conzelmann, Alison Filbey, Maryell Abella, and Sarah Kim"),
            style="margin-top: auto; font-size: 12px; color: black;"
    )


    ),

    # Main content layout with two columns
    ui.layout_columns(
        # First Column: Map Display
        ui.card(
            ui.card_header("Explore ETOD Eligible City-Owned Vacant Lots in Chicago"),
            ui.output_ui("full_map_plot"),
            full_screen=True,
        ),
        
        # Second Column: TIF District Selection and Plot
        ui.card(
            ui.card_header("Explore ETOD Eligible City-Owned Vacant Lots by TIF District"),
            ui.input_select(id="tif", label="Choose a TIF District:", choices=[]),
            ui.output_ui("tif_district_plot"),
            full_screen=True,
        ),
    ),

    ui.layout_column_wrap(
        ui.markdown("# Leveraging Equitable Transit Oriented Development"),
        ui.markdown(
            "The maps above show city-owned vacant lots that are eligible for equitable transit oriented development (ETOD) grant funding and are in Tax Increment Financing (TIF) districts. ETOD eligible means the lots are located within a half mile of 'L' or Metra stops or within a quarter mile of eligible bus corridors. Locating affordable housing developments near transit unlocks funding opportunities and ensures that tenants are connected to jobs and other destinations. By locating affordable housing developments in TIF districts, we ensure that affordability is a central component to the revitalization and redevelopment of historically disinvested communities."),

            ui.markdown("Hover over each vacant lot in the map on the right to show the estimated number of units that could be built on each lot. For more details on the methods used to create these estimates and maps, please see the code repository located [here](https://github.com/claireconzelmann/KIHC-affordable-housing-analysis). The datasets used for this analyses were downloaded from the Chicago Data Portal in March 2025."
        ),
        width="100%"
    )
)

app_ui_page2 = ui.page_sidebar(
    # Sidebar for layer selection
    ui.sidebar(
        ui.input_checkbox_group(
            "buildings",
            "Select what buildings to display:",
            choices=["Vacant Buildings", 
                     "Buildings for Sale"],
            selected=["Vacant Buildings", 
                     "Buildings for Sale"],
        ),
        ui.input_checkbox_group(
            "zones_2",
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
            ui.card_header("Explore Vacant and For Sale Buildings in Chicago"),
            ui.output_ui("chicago_plot"),
            full_screen=True,
        ),
        
        # Second Column: Neighborhood Selection and Plot
        ui.card(
            ui.card_header("Explore Vacant and For Sale Buildings by Neighborhood"),
            ui.input_select(id="neighborhood", label="Choose a Neighborhood:", choices=[]),
            ui.output_ui("neighborhood_plot"),
            full_screen=True,
        ),
    ),

    ui.layout_column_wrap(
        ui.markdown("# Rehabilitating Vacant and For Sale Buildings"),
        ui.markdown(
            "The maps above show vacant and for sale commercial buildings in Chicago. The map on the left also displays a measure of neighborhood-level gentrification, the percent change in average assessed home value from 2000 to 2023, highlighting areas most in need of affordable rental units. By utilizing existing building structures, we decrease construction costs and time and gain access to large office buildings no longer in use."),

            ui.markdown("Hover over each building in the map on the right to show the estimated number of units that could be built with each rehabilitated development. For more details on the methods used to create these estimates and maps, please see the code repository located [here](https://github.com/claireconzelmann/KIHC-affordable-housing-analysis). The datasets used for this analyses were downloaded from the Chicago Data Portal and Crexi Commercial Real Estate online database in March 2025."
        ),
        width="100%"
    )
)

app_ui = ui.page_navbar(
    ui.nav_spacer(),  
    ui.nav_panel("ETOD Eligible Land", app_ui_page1),
    ui.nav_panel("Vacant Buildings and Buildings for Sale", app_ui_page2),
    title="Where Can We Build Affordable Housing in Chicago?",
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
                tooltip_text = f"Zoning: {row['zoning']}<br>Proposed re-zoning: {row['re_zone']}<br>Address: {row['Address']}<br>Estimated # Units: {row['n_units']}"

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


# page 2
    @reactive.calc
    def zone_data_v():
        df = vacant_buildings_gdf
        zones = input.zones_2()  
        if zones:
            filtered_df_vacant = df[df["zone_cat"].isin(zones)]
        else:
            filtered_df_vacant = pd.DataFrame()
        return filtered_df_vacant

    
    @reactive.calc
    def zone_data_s():
        df = sale_buildings_gdf
        zones = input.zones_2()  
        if zones:
            filtered_df_sales = df[df["zone_cat"].isin(zones)]
        else:
            filtered_df_sales = pd.DataFrame()
        return filtered_df_sales
    
    @output
    @render.ui
    def chicago_plot():
        zoned_vacant_buildings = zone_data_v() 
        zoned_sale_buildings = zone_data_s() 
        merged_neighborhoods_gdf['percent_ch'] = merged_neighborhoods_gdf['percent_ch'].apply(lambda x: round(x, 2))
        colormap = branca.colormap.linear.RdPu_09.scale(merged_neighborhoods_gdf['percent_ch'].min(), merged_neighborhoods_gdf['percent_ch'].max())

        # Set default map center (Chicago)
        map_center = [41.8781, -87.6298]

        # Initialize Folium Map
        map_ = folium.Map(location=map_center, zoom_start=11, tiles="CartoDB positron")
        

        folium.GeoJson(
            merged_neighborhoods_gdf.to_crs(epsg=4326),
            name="Neighborhood Percent Change",
            style_function=lambda x: {
                'fillColor': colormap(x['properties']['percent_ch']),  # Apply the color map
                'weight': 1, 
                'fillOpacity': 0.6,
                'color': 'black'
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["Neigh", "percent_ch"], 
                aliases=["Neighborhood", "Percent Change"],
                localize=True  # 
            )
        ).add_to(map_)
        colormap.caption = 'Percent Change in Avg. Assessed Value, 2000-2023'
        colormap.add_to(map_)
       

       # Return the HTML representation of the map
        map_html = map_._repr_html_()  # This gets the HTML representation of the map
        
        # plotting vacant buildings
        if "Vacant Buildings" in input.buildings():
                for _, row in zoned_vacant_buildings.iterrows():
                    lat, lon = row.geometry.centroid.y, row.geometry.centroid.x

                    folium.CircleMarker(
                        location=[lat, lon],
                        popup="Vacant Building",
                        radius=2,
                        color="green",
                        fill=True,
                        fill_color="green",
                        fill_opacity=0.9  
                    ).add_to(map_)

        # plotting buildings for sale
        if "Buildings for Sale" in input.buildings():
                for _, row in zoned_sale_buildings.iterrows():
                    lat, lon = row.geometry.centroid.y, row.geometry.centroid.x

                    folium.CircleMarker(
                        location=[lat, lon],
                        popup="Building for Sale",
                        radius=2,
                        color="black",
                        fill=True,
                        fill_color="black",
                        fill_opacity=0.9
                    ).add_to(map_)

        folium.LayerControl().add_to(map_)

        return ui.HTML(map_._repr_html_())
    
    @reactive.calc
    def neigh_data():
        df = merged_neighborhoods_gdf
        return df[df["Neigh"] == input.neighborhood()]

    @reactive.calc
    def sales_data():
        df = sale_buildings_gdf
        filtered_df = df[df["Neigh"] == input.neighborhood()]
        if input.zones_2():
            filtered_df = filtered_df[filtered_df["zone_cat"].isin(input.zones_2())]

        return filtered_df

    @reactive.calc
    def vacant_data():
        df = vacant_buildings_gdf
        filtered_df = df[df["Neigh"] == input.neighborhood()]
        if input.zones_2():
            filtered_df = filtered_df[filtered_df["zone_cat"].isin(input.zones_2())]

        return filtered_df
    

    @output
    @render.ui
    def neighborhood_plot():
        neigh_df = neigh_data()
        sales_df = sales_data()
        vacant_df = vacant_data()


        # If there's a selected neighborhood, update map center to its centroid
        if not neigh_df.empty:
            centroid = neigh_df.geometry.centroid.unary_union
            map_center = [centroid.y, centroid.x]

        # Initialize Folium map centered at the neighborhood
        map_ = folium.Map(location=map_center, zoom_start=14, tiles = "CartoDB positron")

    # Add vacant buildings with Tooltips
        if "Vacant Buildings" in input.buildings():
            for idx, row in vacant_df.iterrows():
                lat, lon = row.geometry.centroid.y, row.geometry.centroid.x  # Get coordinates
                tooltip_text = f"Zoning: {row['zoning'] if 'zoning' in row else 'N/A'}<br>Proposed re-zoning: {row['re_zone']}<br>Address: {row['Address']}<br>Number of Units: {row['n_units']}"

                folium.Marker(
                    location=[lat, lon],
                    tooltip=tooltip_text,  # Shows on hover
                    popup=tooltip_text,  # Click to see full details
                    icon=folium.Icon(color="green", icon="info-sign")
                ).add_to(map_)
    # Add buildings for sale with Tooltips
        if "Buildings for Sale" in input.buildings():
            for idx, row in sales_df.iterrows():
                lat, lon = row.geometry.centroid.y, row.geometry.centroid.x  # Get coordinates
                tooltip_text = f"Zoning: {row['zoning'] if 'zoning' in row else 'N/A'}<br>Proposed re-zoning: {row['re_zone']}<br>Address: {row['Address']}<br>Number of Units: {row['n_units']}"

                folium.Marker(
                    location=[lat, lon],
                    tooltip=tooltip_text,  # Shows on hover
                    popup=tooltip_text,  # Click to see full details
                    icon=folium.Icon(color="black", icon="info-sign")
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
            <i style="background: green; width: 12px; height: 12px; display: inline-block; border-radius: 2px;"></i> Vacant Buildings <br>
            <i style="background: black; width: 12px; height: 12px; display: inline-block; border-radius: 2px;"></i> Buildings for Sale <br>
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
        neigh_list = merged_neighborhoods_gdf["Neigh"].unique().tolist()
        neigh_list = sorted(neigh_list)
        ui.update_select("neighborhood", choices=neigh_list)



# Run the app
app = App(app_ui, server)