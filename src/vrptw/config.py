"""Configuration settings for VRPTW solver."""

from dataclasses import dataclass


@dataclass
class VRPConfig:
    """Configuration class for VRPTW solver parameters."""

    # Geography / data collection
    center_lat: float = 49.504896
    center_lon: float = 11.015822
    radius_km: float = 50
    osrm_url: str = "http://127.0.0.1:9001"

    # Time windows (seconds from midnight)
    client_tw_start: int = 7 * 3600  # 07:00
    client_tw_end: int = 9 * 3600  # 09:00
    depot_tw_start: int = 5 * 3600  # 05:00
    depot_tw_end: int = 19 * 3600  # 19:00

    # Service & capacity
    service_time_sec: int = 600  # 10 min per stop
    vehicle_capacity: int = 50  # Each pharmacy demand=1
    vehicle_fixed_cost: int = 5000  # Fixed cost per vehicle

    # Solver control
    initial_vehicle_count: int | None = 50  # None => auto lower bound
    auto_increase_vehicles: bool = True  # Escalate if infeasible
    time_limit_sec: int = 20  # Search limit

    # Plotting
    plot_png: bool = True
    plot_path: str = "vrp_routes.png"
    plot_show: bool = False

    # Interactive map
    folium_map: bool = True  # Set True to generate interactive map
    folium_path: str = "vrp_routes.html"
