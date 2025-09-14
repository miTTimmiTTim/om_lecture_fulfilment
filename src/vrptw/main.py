"""Main execution logic for VRPTW solver."""

import time
from typing import Any

from .config import VRPConfig
from .data import get_distance_matrix_osrm, get_pharmacies_overpass
from .solver import VRPResult, solve_vrptw
from .utils import summarize_result
from .visualization import build_folium_map, plot_vrp_matplotlib


def main(
    config: VRPConfig | None = None, pharmacies_override: list[dict[str, str | float]] | None = None
) -> VRPResult:
    """Execute complete VRPTW pipeline.

    Args:
        config: VRPTW configuration (uses default if None)
        pharmacies_override: Pre-filtered pharmacy list (skips Overpass API if provided)

    Returns:
        VRPResult containing solution and statistics

    Raises:
        Exception: If any stage of the pipeline fails
    """
    if config is None:
        config = VRPConfig()

    print("=== VRPTW SOLVER PIPELINE ===")
    print(
        f"Configuration: {config.center_lat:.4f}°N, {config.center_lon:.4f}°E, "
        f"radius {config.radius_km}km"
    )

    start_time = time.time()

    try:
        # Stage 1: Fetch pharmacies from Overpass API (or use override)
        if pharmacies_override is not None:
            print("\n1. Using provided pharmacy data...")
            pharmacies = pharmacies_override
            print(f"   → Using {len(pharmacies)} pre-filtered pharmacies")
        else:
            print("\n1. Fetching pharmacies from OpenStreetMap...")
            pharmacies = get_pharmacies_overpass(
                config.center_lat, config.center_lon, config.radius_km
            )
            print(f"   → Found {len(pharmacies)} pharmacies")

        if not pharmacies:
            print("ERROR: No pharmacies found in specified area")
            return VRPResult([], 0.0, 0, 0, status="NO_DATA")

        # Stage 2: Build OSRM distance/time matrices
        print("\n2. Building OSRM distance/time matrices...")
        dist_df, dur_df = get_distance_matrix_osrm(
            config.center_lat, config.center_lon, pharmacies, config.osrm_url
        )

        if dist_df.empty or dur_df.empty:
            print("ERROR: Failed to build OSRM matrices")
            return VRPResult([], 0.0, 0, 0, status="OSRM_ERROR")

        matrix_size = len(dist_df)
        print(f"   → Built {matrix_size}×{matrix_size} matrices")

        # Stage 3: Solve VRPTW problem
        print("\n3. Solving VRPTW with OR-Tools...")
        print(
            f"   Parameters: {config.initial_vehicle_count} vehicles (max), "
            f"{config.vehicle_capacity} capacity, {config.time_limit_sec}s limit"
        )

        result = solve_vrptw(
            depot_lat=config.center_lat,
            depot_lon=config.center_lon,
            radius_km=config.radius_km,
            vehicle_count=config.initial_vehicle_count,
            vehicle_capacity=config.vehicle_capacity,
            service_time_sec=config.service_time_sec,
            vehicle_fixed_cost=config.vehicle_fixed_cost,
            client_tw=(config.client_tw_start, config.client_tw_end),
            depot_tw=(config.depot_tw_start, config.depot_tw_end),
            osrm_url=config.osrm_url,
            time_limit_sec=config.time_limit_sec,
            auto_increase_vehicles=config.auto_increase_vehicles,
        )

        print(f"   → Solution status: {result.status}")

        if result.status != "OK":
            print(f"ERROR: Solver failed with status: {result.status}")
            return result

        # Stage 4: Generate visualizations
        print("\n4. Generating visualizations...")

        if config.plot_png:
            print(f"   Creating static plot: {config.plot_path}")
            plot_vrp_matplotlib(
                result=result,
                depot_lat=config.center_lat,
                depot_lon=config.center_lon,
                output_path=config.plot_path,
                show_plot=config.plot_show,
            )

        if config.folium_map:
            print(f"   Creating interactive map: {config.folium_path}")
            build_folium_map(
                result=result,
                depot_lat=config.center_lat,
                depot_lon=config.center_lon,
                osrm_url=config.osrm_url,
                output_path=config.folium_path,
            )

        # Stage 5: Print summary
        print("\n5. Solution Summary:")
        summarize_result(result)

        elapsed_time = time.time() - start_time
        print(f"\n=== PIPELINE COMPLETED in {elapsed_time:.1f}s ===")

        return result

    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"\nERROR: Pipeline failed after {elapsed_time:.1f}s: {e}")
        raise


def main_with_custom_config(**kwargs: Any) -> VRPResult:
    """Execute VRPTW pipeline with custom configuration parameters.

    Args:
        **kwargs: Configuration parameters to override defaults

    Returns:
        VRPResult containing solution and statistics

    Example:
        result = main_with_custom_config(
            center_lat=49.5,
            center_lon=11.0,
            radius_km=30,
            vehicle_capacity=40
        )
    """
    config = VRPConfig()

    # Override config with provided kwargs
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
        else:
            print(f"WARNING: Unknown config parameter: {key}")

    return main(config)


def quick_test() -> VRPResult:
    """Quick test with minimal configuration for development/debugging.

    Returns:
        VRPResult from small test scenario
    """
    print("Running VRPTW quick test...")

    config = VRPConfig(
        radius_km=10,  # Smaller radius for faster execution
        initial_vehicle_count=5,
        time_limit_sec=10,  # Shorter solve time
        plot_show=False,
        folium_map=True,
    )

    return main(config)


if __name__ == "__main__":
    # Direct execution for testing
    try:
        result = main()
        if result.status == "OK":
            print("✓ VRPTW execution completed successfully")
        else:
            print(f"✗ VRPTW execution failed: {result.status}")
    except Exception as e:
        print(f"✗ VRPTW execution error: {e}")
        raise
