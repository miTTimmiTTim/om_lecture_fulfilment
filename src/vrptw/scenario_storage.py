"""Data storage utilities for VRPTW scenarios using Polars."""

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

import polars as pl

from .data.osrm import get_route_geometry
from .scenario_config import ScenarioParams
from .solver import VRPResult


def calculate_pharmacy_distances(
    pharmacies: list[dict[str, str | float]], center_lat: float, center_lon: float
) -> pl.DataFrame:
    """Convert pharmacy list to Polars DataFrame with distance calculations.

    Args:
        pharmacies: List of pharmacy dictionaries from Overpass
        center_lat: Depot latitude for distance calculation
        center_lon: Depot longitude for distance calculation

    Returns:
        Polars DataFrame with pharmacy data and distance_from_center_km column
    """
    # Handle empty case
    if not pharmacies:
        return pl.DataFrame(
            schema={
                "id": pl.Utf8,
                "name": pl.Utf8,
                "lat": pl.Float64,
                "lon": pl.Float64,
                "distance_from_center_km": pl.Float64,
            }
        )

    # Convert to Polars DataFrame
    df = pl.DataFrame(pharmacies)

    # Calculate distances using haversine formula
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate great circle distance between two points in km."""
        R = 6371  # Earth's radius in km

        # Convert degrees to radians
        lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
        lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)

        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    # Add distance column
    df = df.with_columns(
        [
            pl.struct(["lat", "lon"])
            .map_elements(
                lambda row: haversine_distance(center_lat, center_lon, row["lat"], row["lon"]),
                return_dtype=pl.Float64,
            )
            .alias("distance_from_center_km")
        ]
    )

    return df


def collect_route_geometries(
    result: VRPResult, osrm_url: str = "http://127.0.0.1:9001", timeout: int = 30
) -> dict[str, Any]:
    """Collect OSRM route geometries for all route segments.

    Args:
        result: VRP solution result
        osrm_url: OSRM server URL
        timeout: Request timeout in seconds

    Returns:
        Dictionary with route data including geometries for offline use
    """
    routes_with_geometry = []

    for route in result.routes:
        if not route["stops"] or len(route["stops"]) < 2:
            continue

        route_data = {
            "vehicle": route["vehicle"],
            "load": route["load"],
            "stops": route["stops"],
            "segments": [],
        }

        # Collect geometry for each route segment
        for i in range(len(route["stops"]) - 1):
            start_stop = route["stops"][i]
            end_stop = route["stops"][i + 1]

            try:
                # Get OSRM route geometry
                geometry = get_route_geometry(
                    osrm_url,
                    start_stop["lat"],
                    start_stop["lon"],
                    end_stop["lat"],
                    end_stop["lon"],
                )

                segment_data = {"start": start_stop, "end": end_stop, "geometry": geometry}
                route_data["segments"].append(segment_data)

            except Exception as e:
                # Store segment without geometry if OSRM fails
                segment_data = {
                    "start": start_stop,
                    "end": end_stop,
                    "geometry": [
                        [start_stop["lat"], start_stop["lon"]],
                        [end_stop["lat"], end_stop["lon"]],
                    ],
                    "error": str(e),
                }
                route_data["segments"].append(segment_data)

        routes_with_geometry.append(route_data)

    return {
        "routes": routes_with_geometry,
        "total_distance_km": result.total_distance_km,
        "total_time_sec": result.total_time_sec,
        "vehicles_used": result.vehicles_used,
        "status": result.status,
    }


def initialize_scenario_data_directory(output_dir: Path) -> None:
    """Initialize the scenario data directory structure.

    Args:
        output_dir: Base directory for scenario data
    """
    output_dir.mkdir(exist_ok=True)
    (output_dir / "routes").mkdir(exist_ok=True)

    # Create metadata file
    metadata = {
        "dataset": "VRPTW Scenario Analysis Dataset",
        "created": datetime.now().isoformat(),
        "description": (
            "Vehicle Routing Problem with Time Windows optimization results for multiple scenarios"
        ),
        "parameters": {
            "radii": list(range(5, 80, 5)),
            "client_time_window_lengths_hours": list(range(2, 11)),
            "client_time_window_start": "07:00",
            "depot_time_window": "05:00-19:00",
        },
        "total_scenarios": 135,
        "files": {
            "pharmacies.parquet": "All pharmacy locations with distance calculations",
            "scenarios.csv": "Summary metrics for all scenarios",
            "routes/scenario_*.json": "Detailed route data with OSRM geometries",
            "completed.txt": "Checkpoint file for resumable execution",
        },
    }

    with open(output_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)


def store_pharmacies_data(df_pharmacies: pl.DataFrame, output_dir: Path) -> None:
    """Store pharmacy data as Parquet file.

    Args:
        df_pharmacies: Polars DataFrame with pharmacy data
        output_dir: Output directory
    """
    output_path = output_dir / "pharmacies.parquet"
    df_pharmacies.write_parquet(output_path)
    print(f"Stored pharmacy data: {output_path} ({len(df_pharmacies)} pharmacies)")


def store_scenario_result(
    scenario: ScenarioParams,
    result: VRPResult,
    route_geometries: dict[str, Any],
    pharmacies_count: int,
    execution_time_sec: float,
    output_dir: Path,
) -> None:
    """Store results for a single scenario.

    Args:
        scenario: Scenario parameters
        result: VRP solution result
        route_geometries: Route data with geometries
        pharmacies_count: Number of pharmacies in this scenario
        execution_time_sec: Execution time for this scenario
        output_dir: Output directory
    """
    # Store detailed route data with geometries
    route_data = {
        "scenario_id": scenario.scenario_id,
        "parameters": {
            "radius_km": scenario.radius_km,
            "client_tw_hours": scenario.client_tw_hours,
            "client_tw_start": scenario.client_tw_start,
            "client_tw_end": scenario.client_tw_end,
            "depot_tw_start": scenario.depot_tw_start,
            "depot_tw_end": scenario.depot_tw_end,
        },
        "solution": route_geometries,
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "pharmacies_count": pharmacies_count,
            "execution_time_sec": execution_time_sec,
        },
    }

    route_file = output_dir / "routes" / f"scenario_{scenario.scenario_id}.json"
    with open(route_file, "w") as f:
        json.dump(route_data, f, indent=2)

    # Append scenario summary to CSV
    scenario_data = {
        "scenario_id": scenario.scenario_id,
        "radius_km": scenario.radius_km,
        "client_tw_hours": scenario.client_tw_hours,
        "client_tw_start": scenario.client_tw_start,
        "client_tw_end": scenario.client_tw_end,
        "depot_tw_start": scenario.depot_tw_start,
        "depot_tw_end": scenario.depot_tw_end,
        "pharmacies_count": pharmacies_count,
        "vehicles_used": result.vehicles_used,
        "total_distance_km": result.total_distance_km,
        "total_time_sec": result.total_time_sec,
        "execution_time_sec": execution_time_sec,
        "status": result.status,
        "timestamp": datetime.now().isoformat(),
    }

    scenarios_file = output_dir / "scenarios.csv"
    df_scenario = pl.DataFrame([scenario_data])

    # Append to existing file or create new one
    if scenarios_file.exists():
        df_existing = pl.read_csv(scenarios_file)
        df_combined = pl.concat([df_existing, df_scenario])
        df_combined.write_csv(scenarios_file)
    else:
        df_scenario.write_csv(scenarios_file)

    print(
        f"Stored scenario {scenario.scenario_id}: {result.vehicles_used} vehicles, "
        f"{result.total_distance_km:.1f}km"
    )


def load_completed_scenarios(output_dir: Path) -> set[str]:
    """Load set of completed scenario IDs for resumability.

    Args:
        output_dir: Output directory

    Returns:
        Set of completed scenario IDs
    """
    completed_file = output_dir / "completed.txt"
    if not completed_file.exists():
        return set()

    with open(completed_file) as f:
        return set(line.strip() for line in f if line.strip())


def mark_scenario_completed(scenario_id: str, output_dir: Path) -> None:
    """Mark a scenario as completed for resumability.

    Args:
        scenario_id: ID of completed scenario
        output_dir: Output directory
    """
    completed_file = output_dir / "completed.txt"
    with open(completed_file, "a") as f:
        f.write(f"{scenario_id}\n")


def get_scenario_summary_stats(output_dir: Path) -> dict[str, Any]:
    """Get summary statistics from completed scenarios.

    Args:
        output_dir: Output directory

    Returns:
        Dictionary with summary statistics
    """
    scenarios_file = output_dir / "scenarios.csv"
    if not scenarios_file.exists():
        return {"message": "No scenarios completed yet"}

    df = pl.read_csv(scenarios_file)

    stats = {
        "total_scenarios": len(df),
        "successful_scenarios": len(df.filter(pl.col("status") == "OK")),
        "failed_scenarios": len(df.filter(pl.col("status") != "OK")),
        "total_pharmacies": df["pharmacies_count"].sum(),
        "total_distance_km": df.filter(pl.col("status") == "OK")["total_distance_km"].sum(),
        "total_vehicles_used": df.filter(pl.col("status") == "OK")["vehicles_used"].sum(),
        "avg_execution_time_sec": df["execution_time_sec"].mean(),
        "min_vehicles": df.filter(pl.col("status") == "OK")["vehicles_used"].min(),
        "max_vehicles": df.filter(pl.col("status") == "OK")["vehicles_used"].max(),
        "radius_range": f"{df['radius_km'].min()}-{df['radius_km'].max()} km",
        "time_window_range": f"{df['client_tw_hours'].min()}-{df['client_tw_hours'].max()} hours",
    }

    return stats
