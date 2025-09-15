"""Configuration and parameter generation for VRPTW scenarios."""

import itertools
from dataclasses import dataclass

from .config import VRPConfig


@dataclass
class ScenarioParams:
    """Parameters for a single VRPTW scenario."""

    scenario_id: str
    radius_km: float
    client_tw_hours: int
    client_tw_start: int  # seconds since midnight
    client_tw_end: int  # seconds since midnight
    depot_tw_start: int  # seconds since midnight
    depot_tw_end: int  # seconds since midnight
    service_time_sec: int  # service time per stop in seconds


def generate_scenario_id(radius_km: float, client_tw_hours: int, service_time_sec: int) -> str:
    """Generate scenario ID from parameters.

    Args:
        radius_km: Search radius in kilometers
        client_tw_hours: Client time window length in hours
        service_time_sec: Service time per stop in seconds

    Returns:
        Scenario ID in format 'RR_HH_SS' (e.g., '05_02_01', '75_10_09')
    """
    service_time_min = service_time_sec // 60
    return f"{int(radius_km):02d}_{client_tw_hours:02d}_{service_time_min:02d}"


def generate_all_scenarios() -> list[ScenarioParams]:
    """Generate all 675 scenario parameter combinations.

    Returns:
        List of ScenarioParams for all radius/time window/service time combinations
    """
    # Search radii: 5-75km in 5km steps (15 values)
    radii = list(range(5, 80, 5))

    # Client time window lengths: 2-10 hours (9 values)
    tw_lengths = list(range(2, 11))

    # Service times: 1-9 minutes in 2-minute steps (5 values)
    service_times_sec = [60, 180, 300, 420, 540]  # 1, 3, 5, 7, 9 minutes

    # Fixed parameters
    client_tw_start = 7 * 3600  # 07:00 in seconds
    depot_tw_start = 5 * 3600  # 05:00 in seconds
    depot_tw_end = 19 * 3600  # 19:00 in seconds

    scenarios = []
    for radius, tw_hours, service_time in itertools.product(radii, tw_lengths, service_times_sec):
        client_tw_end = client_tw_start + (tw_hours * 3600)
        scenario_id = generate_scenario_id(radius, tw_hours, service_time)

        scenarios.append(
            ScenarioParams(
                scenario_id=scenario_id,
                radius_km=radius,
                client_tw_hours=tw_hours,
                client_tw_start=client_tw_start,
                client_tw_end=client_tw_end,
                depot_tw_start=depot_tw_start,
                depot_tw_end=depot_tw_end,
                service_time_sec=service_time,
            )
        )

    return scenarios


def create_vrp_config_for_scenario(
    scenario: ScenarioParams, base_config: VRPConfig | None = None
) -> VRPConfig:
    """Create VRPConfig for a specific scenario.

    Args:
        scenario: Scenario parameters
        base_config: Base configuration to modify (uses default if None)

    Returns:
        VRPConfig configured for the scenario
    """
    if base_config is None:
        base_config = VRPConfig()

    # Create new config with scenario-specific parameters
    return VRPConfig(
        # Geographic parameters from scenario
        center_lat=base_config.center_lat,
        center_lon=base_config.center_lon,
        radius_km=scenario.radius_km,
        # Time window parameters from scenario
        client_tw_start=scenario.client_tw_start,
        client_tw_end=scenario.client_tw_end,
        depot_tw_start=scenario.depot_tw_start,
        depot_tw_end=scenario.depot_tw_end,
        # Service time from scenario (key change!)
        service_time_sec=scenario.service_time_sec,
        # Keep all other parameters from base config
        vehicle_capacity=base_config.vehicle_capacity,
        vehicle_fixed_cost=base_config.vehicle_fixed_cost,
        initial_vehicle_count=base_config.initial_vehicle_count,
        auto_increase_vehicles=base_config.auto_increase_vehicles,
        time_limit_sec=base_config.time_limit_sec,
        osrm_url=base_config.osrm_url,
        plot_png=base_config.plot_png,
        plot_path=base_config.plot_path,
        plot_show=base_config.plot_show,
        folium_map=base_config.folium_map,
        folium_path=base_config.folium_path,
    )


def get_scenario_summary() -> str:
    """Get human-readable summary of all scenarios.

    Returns:
        Formatted string describing scenario parameters
    """
    scenarios = generate_all_scenarios()

    radii = sorted(set(s.radius_km for s in scenarios))
    tw_lengths = sorted(set(s.client_tw_hours for s in scenarios))
    service_times = sorted(set(s.service_time_sec for s in scenarios))

    summary = f"""VRPTW Scenario Generator Summary:

Total Scenarios: {len(scenarios)}

Search Radii: {len(radii)} values
  - Range: {min(radii)}-{max(radii)} km in {radii[1] - radii[0]} km steps
  - Values: {radii}

Client Time Windows: {len(tw_lengths)} values
  - Start: Always 07:00
  - Lengths: {tw_lengths} hours
  - End times: 09:00 to 17:00

Service Times: {len(service_times)} values
  - Range: {min(service_times) // 60}-{max(service_times) // 60} minutes
  - Values: {[t // 60 for t in service_times]} minutes

Depot Time Windows: Fixed
  - Start: 05:00
  - End: 19:00

Scenario ID Format: 'radius_hours_servicemins' (e.g., '05_02_01', '75_10_09')
Expected Runtime: 5-20 hours ({len(scenarios)} scenarios)
"""

    return summary


def get_scenarios_by_radius(radius_km: float) -> list[ScenarioParams]:
    """Get all scenarios for a specific radius.

    Args:
        radius_km: Search radius to filter by

    Returns:
        List of scenarios matching the radius
    """
    all_scenarios = generate_all_scenarios()
    return [s for s in all_scenarios if s.radius_km == radius_km]


def get_scenarios_by_time_window(tw_hours: int) -> list[ScenarioParams]:
    """Get all scenarios for a specific time window length.

    Args:
        tw_hours: Time window length in hours to filter by

    Returns:
        List of scenarios matching the time window length
    """
    all_scenarios = generate_all_scenarios()
    return [s for s in all_scenarios if s.client_tw_hours == tw_hours]
