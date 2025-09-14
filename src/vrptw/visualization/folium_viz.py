"""Folium-based interactive visualization for VRPTW solutions."""

import colorsys

import folium
from folium import plugins

from ..data.osrm import get_route_geometry
from ..solver import VRPResult


def generate_colors(n: int) -> list[str]:
    """Generate n visually distinct colors using HSV color space.

    Args:
        n: Number of colors to generate

    Returns:
        List of hex color strings
    """
    if n == 0:
        return []
    if n == 1:
        return ["#1f77b4"]

    colors = []
    for i in range(n):
        hue = i / n  # Distribute hues evenly around color wheel
        saturation = 0.8 + (i % 3) * 0.1  # Vary saturation slightly (0.8-1.0)
        value = 0.9 + (i % 2) * 0.1  # Vary brightness slightly (0.9-1.0)

        rgb = colorsys.hsv_to_rgb(hue, saturation, value)
        hex_color = f"#{int(rgb[0] * 255):02x}{int(rgb[1] * 255):02x}{int(rgb[2] * 255):02x}"
        colors.append(hex_color)

    return colors


def build_folium_map(
    result: VRPResult,
    depot_lat: float,
    depot_lon: float,
    osrm_url: str = "http://127.0.0.1:9001",
    output_path: str = "vrp_routes.html",
) -> None:
    """Build interactive Folium map of VRPTW solution.

    Args:
        result: VRPTW solution result
        depot_lat: Depot latitude
        depot_lon: Depot longitude
        osrm_url: OSRM server URL for route geometry
        output_path: Path to save the HTML map
    """
    if result.status != "OK" or not result.routes:
        print(f"No solution to map (status: {result.status})")
        return

    # Create base map centered on depot with CartoDB Light style
    m = folium.Map(location=[depot_lat, depot_lon], zoom_start=11, tiles=None)

    # Add CartoDB Light basemap to match original style
    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        attr=(
            '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> '
            'contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        ),
        name="CartoDB Light",
        overlay=False,
        control=True,
    ).add_to(m)

    # Add depot marker with warehouse/building icon
    folium.Marker(
        [depot_lat, depot_lon],
        popup=folium.Popup("<b>🏭 DEPOT</b><br/>Distribution Center", max_width=200),
        tooltip="Distribution Center",
        icon=folium.Icon(color="red", icon="warehouse", prefix="fa"),
    ).add_to(m)

    # Generate colors for each vehicle
    colors = generate_colors(result.vehicles_used)

    # Track plotted pharmacies to avoid duplicates
    plotted_pharmacies = set()

    # Add routes for each vehicle
    routes_added = 0
    for i, route in enumerate(result.routes):
        if not route["stops"] or len(route["stops"]) < 2:
            continue

        color = colors[i % len(colors)] if colors else "#1f77b4"
        routes_added += 1

        # Create feature group for this vehicle
        vehicle_group = folium.FeatureGroup(
            name=f"Vehicle {route['vehicle']} ({len(route['stops']) - 2} stops)",
            show=True,  # Ensure layer is visible by default
        )

        # Process route stops
        route_coords = []
        for j, stop in enumerate(route["stops"]):
            stop_lat, stop_lon = stop["lat"], stop["lon"]
            route_coords.append([stop_lat, stop_lon])

            # Add pharmacy markers (skip depot)
            if not stop["is_depot"]:
                pharmacy_key = (stop["lat"], stop["lon"])
                if pharmacy_key not in plotted_pharmacies:
                    # Format arrival time
                    arrival_time = stop["arrival_time"]
                    hours = arrival_time // 3600
                    minutes = (arrival_time % 3600) // 60
                    time_str = f"{hours:02d}:{minutes:02d}"

                    # Use pharmacy icon marker instead of circle
                    folium.Marker(
                        [stop_lat, stop_lon],
                        popup=folium.Popup(
                            f"<b>💊 {stop['name']}</b><br/>"
                            f"Vehicle: {route['vehicle']}<br/>"
                            f"Stop: {j}<br/>"
                            f"Arrival: {time_str}",
                            max_width=250,
                        ),
                        tooltip=f"{stop['name']} ({time_str})",
                        icon=folium.Icon(
                            color="blue",
                            icon="plus-square",  # Medical cross symbol
                            prefix="fa",
                        ),
                    ).add_to(vehicle_group)
                    plotted_pharmacies.add(pharmacy_key)

        # Add route lines with OSRM geometry
        for j in range(len(route["stops"]) - 1):
            start_stop = route["stops"][j]
            end_stop = route["stops"][j + 1]

            # Get OSRM route geometry between consecutive stops
            route_geometry = get_route_geometry(
                osrm_url, start_stop["lat"], start_stop["lon"], end_stop["lat"], end_stop["lon"]
            )

            # Add route segment with OSRM geometry - match original style
            route_line = folium.PolyLine(
                locations=route_geometry,
                color=color,
                weight=3,  # Slightly thinner lines
                opacity=0.7,  # Match original opacity
                popup=f"Vehicle {route['vehicle']}: {start_stop['name']} → {end_stop['name']}",
            )
            route_line.add_to(vehicle_group)

            # Add direction arrows on the route segment
            if len(route_geometry) >= 2:
                plugins.PolyLineTextPath(
                    route_line,
                    "  ►  ",
                    repeat=True,
                    offset=7,
                    attributes={"fill": color, "font-weight": "bold", "font-size": "10"},
                ).add_to(vehicle_group)

        # Add vehicle group to map
        vehicle_group.add_to(m)

    # Add layer control to toggle vehicle routes
    folium.LayerControl(collapsed=False).add_to(m)

    # Add solution summary to map with cleaner styling
    solution_info = f"""
    <div style='position: fixed;
                top: 10px; right: 10px; width: 220px; height: auto;
                background-color: rgba(255,255,255,0.9);
                border: 1px solid #ccc;
                border-radius: 5px;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
                z-index: 9999;
                font-size: 13px;
                padding: 12px;
                font-family: Arial, sans-serif;'>
    <h4 style='margin-top: 0; color: #333; font-size: 16px;'>VRPTW Solution</h4>
    <div style='color: #555;'>
    <b>Vehicles:</b> {result.vehicles_used}<br/>
    <b>Distance:</b> {result.total_distance_km:.1f} km<br/>
    <b>Time:</b> {result.total_time_sec / 3600:.1f} hours<br/>
    <b>Pharmacies:</b> {sum(len(r["stops"]) - 2 for r in result.routes)}<br/>
    <b>Status:</b> <span style='color: #28a745;'>{result.status}</span>
    </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(solution_info))

    # Add minimap
    minimap = plugins.MiniMap(toggle_display=True)
    m.add_child(minimap)

    # Add measure tool
    plugins.MeasureControl(primary_length_unit="kilometers").add_to(m)

    # Add fullscreen option
    plugins.Fullscreen().add_to(m)

    # Save map
    m.save(output_path)
    print(f"Interactive map saved to: {output_path} (added {routes_added} vehicle routes)")


def create_overview_map(
    depot_lat: float,
    depot_lon: float,
    pharmacies: list[dict[str, str | float]],
    output_path: str = "pharmacies_overview.html",
) -> None:
    """Create overview map showing all available pharmacies.

    Args:
        depot_lat: Depot latitude
        depot_lon: Depot longitude
        pharmacies: List of pharmacy dictionaries
        output_path: Path to save the HTML map
    """
    # Create base map
    m = folium.Map(location=[depot_lat, depot_lon], zoom_start=9, tiles="OpenStreetMap")

    # Add depot marker with warehouse icon
    folium.Marker(
        [depot_lat, depot_lon],
        popup="🏭 DEPOT - Distribution Center",
        tooltip="Distribution Center",
        icon=folium.Icon(color="red", icon="warehouse", prefix="fa"),
    ).add_to(m)

    # Add all pharmacies with medical icons
    for pharmacy in pharmacies:
        folium.Marker(
            [pharmacy["lat"], pharmacy["lon"]],
            popup=f"💊 {pharmacy['name']}",
            tooltip=pharmacy["name"],
            icon=folium.Icon(color="lightblue", icon="plus-square", prefix="fa"),
        ).add_to(m)

    # Add search radius circle
    folium.Circle(
        [depot_lat, depot_lon],
        radius=50000,  # 50km in meters
        popup="50km Search Radius",
        color="gray",
        fillColor="gray",
        fillOpacity=0.1,
        weight=2,
        dashArray="5,5",
    ).add_to(m)

    # Add pharmacy count info
    info_html = f"""
    <div style='position: fixed;
                top: 10px; right: 10px; width: 200px; height: auto;
                background-color: white; border:2px solid grey; z-index:9999;
                font-size:14px; padding: 10px;'>
    <h4>Pharmacy Overview</h4>
    <b>Total Pharmacies:</b> {len(pharmacies)}<br/>
    <b>Search Radius:</b> 50 km<br/>
    <b>Center:</b> Depot
    </div>
    """
    m.get_root().html.add_child(folium.Element(info_html))

    # Save map
    m.save(output_path)
    print(f"Pharmacy overview map saved to: {output_path}")
