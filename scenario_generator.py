#!/usr/bin/env python3
"""VRPTW Scenario Generator - Generate optimization results for multiple scenarios."""

import sys
import time
from pathlib import Path

# Add src directory to Python path for imports
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

import argparse
from datetime import datetime

from tqdm import tqdm

from vrptw.config import VRPConfig
from vrptw.data.overpass import get_pharmacies_overpass
from vrptw.main import main as run_vrp
from vrptw.scenario_config import (
    create_vrp_config_for_scenario,
    generate_all_scenarios,
)
from vrptw.scenario_storage import (
    calculate_pharmacy_distances,
    collect_route_geometries,
    get_scenario_summary_stats,
    initialize_scenario_data_directory,
    load_completed_scenarios,
    mark_scenario_completed,
    store_pharmacies_data,
    store_scenario_result,
)


def run_single_scenario(
    scenario, base_config: VRPConfig, output_dir: Path, all_pharmacies_df
) -> tuple[bool, float]:
    """Run optimization for a single scenario.

    Args:
        scenario: ScenarioParams for this scenario
        base_config: Base VRP configuration
        output_dir: Output directory for results
        all_pharmacies_df: Polars DataFrame with all pharmacy data

    Returns:
        Tuple of (success, execution_time_sec)
    """
    start_time = time.time()

    try:
        # Create scenario-specific config
        config = create_vrp_config_for_scenario(scenario, base_config)

        # Filter pharmacies by radius (using pre-computed distances)
        scenario_pharmacies_df = all_pharmacies_df.filter(
            all_pharmacies_df["distance_from_center_km"] <= scenario.radius_km
        )

        # Convert back to list format for compatibility with existing pipeline
        pharmacies_list = scenario_pharmacies_df.drop("distance_from_center_km").to_dicts()

        if len(pharmacies_list) == 0:
            print(f"  No pharmacies found for radius {scenario.radius_km}km - skipping")
            execution_time = time.time() - start_time
            return False, execution_time

        # Run VRP optimization with pre-filtered pharmacies
        result = run_vrp(config, pharmacies_override=pharmacies_list)

        # Collect route geometries for offline use
        route_geometries = collect_route_geometries(result, config.osrm_url)

        # Store results
        execution_time = time.time() - start_time
        store_scenario_result(
            scenario=scenario,
            result=result,
            route_geometries=route_geometries,
            pharmacies_count=len(pharmacies_list),
            execution_time_sec=execution_time,
            output_dir=output_dir,
        )

        # Mark as completed
        mark_scenario_completed(scenario.scenario_id, output_dir)

        return True, execution_time

    except Exception as e:
        execution_time = time.time() - start_time
        print(f"  Error in scenario {scenario.scenario_id}: {e}")
        return False, execution_time


def main():
    """Main scenario generator function."""
    parser = argparse.ArgumentParser(description="Generate VRPTW scenarios for analysis")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="scenario_data",
        help="Output directory for scenario data (default: scenario_data)",
    )
    parser.add_argument(
        "--test-run",
        action="store_true",
        help="Run test with only 4 scenarios (2 radii × 2 time windows)",
    )
    parser.add_argument(
        "--resume", action="store_true", help="Resume from previously completed scenarios"
    )
    parser.add_argument(
        "--max-radius", type=int, default=75, help="Maximum radius for scenarios (default: 75km)"
    )

    args = parser.parse_args()
    output_dir = Path(args.output_dir)

    print("🚀 VRPTW Scenario Generator")
    print("=" * 50)

    # Initialize output directory
    initialize_scenario_data_directory(output_dir)

    # Load base configuration
    base_config = VRPConfig()
    print(
        f"Base configuration loaded (center: {base_config.center_lat:.4f}, "
        f"{base_config.center_lon:.4f})"
    )

    # Generate scenario list
    if args.test_run:
        print("\n🧪 Test run mode: Limited scenarios")
        # Test run: Only 2 radii × 2 time windows = 4 scenarios
        from vrptw.scenario_config import ScenarioParams, generate_scenario_id

        scenarios = []
        for radius in [10, 30]:  # 2 radii
            for tw_hours in [4, 8]:  # 2 time windows
                client_tw_start = 7 * 3600
                client_tw_end = client_tw_start + (tw_hours * 3600)
                scenarios.append(
                    ScenarioParams(
                        scenario_id=generate_scenario_id(radius, tw_hours),
                        radius_km=radius,
                        client_tw_hours=tw_hours,
                        client_tw_start=client_tw_start,
                        client_tw_end=client_tw_end,
                        depot_tw_start=5 * 3600,
                        depot_tw_end=19 * 3600,
                    )
                )
    else:
        scenarios = generate_all_scenarios()
        # Filter by max radius if specified
        if args.max_radius < 75:
            scenarios = [s for s in scenarios if s.radius_km <= args.max_radius]

    print(f"Generated {len(scenarios)} scenarios")

    # Load completed scenarios for resumability
    completed_scenarios = set()
    if args.resume:
        completed_scenarios = load_completed_scenarios(output_dir)
        if completed_scenarios:
            print(f"Resuming: {len(completed_scenarios)} scenarios already completed")

    # Filter out completed scenarios
    remaining_scenarios = [s for s in scenarios if s.scenario_id not in completed_scenarios]

    if not remaining_scenarios:
        print("✅ All scenarios already completed!")
        stats = get_scenario_summary_stats(output_dir)
        print("\nFinal Summary:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        return

    print(f"Scenarios to process: {len(remaining_scenarios)}")

    # Collect all pharmacy data once (for maximum radius)
    max_radius = max(s.radius_km for s in scenarios)
    print(f"\n📍 Collecting pharmacy data (radius: {max_radius}km)...")

    all_pharmacies = get_pharmacies_overpass(
        center_lat=base_config.center_lat,
        center_lon=base_config.center_lon,
        radius_km=max_radius,
        timeout=30,  # Default timeout
    )

    # Convert to Polars DataFrame with distance calculations
    print("📊 Calculating pharmacy distances...")
    all_pharmacies_df = calculate_pharmacy_distances(
        all_pharmacies, base_config.center_lat, base_config.center_lon
    )

    # Store pharmacy data (once for all scenarios)
    store_pharmacies_data(all_pharmacies_df, output_dir)

    print(f"Found {len(all_pharmacies_df)} total pharmacies")

    # Process scenarios with progress bar
    print(f"\n🔄 Processing {len(remaining_scenarios)} scenarios...")
    start_time = datetime.now()

    successful_count = 0
    failed_count = 0
    total_execution_time = 0

    with tqdm(remaining_scenarios, desc="Scenarios", unit="scenario") as pbar:
        for scenario in pbar:
            pbar.set_description(f"Scenario {scenario.scenario_id}")

            success, execution_time = run_single_scenario(
                scenario=scenario,
                base_config=base_config,
                output_dir=output_dir,
                all_pharmacies_df=all_pharmacies_df,
            )

            if success:
                successful_count += 1
            else:
                failed_count += 1

            total_execution_time += execution_time

            # Update progress bar with stats
            pbar.set_postfix(
                {
                    "success": successful_count,
                    "failed": failed_count,
                    "avg_time": f"{total_execution_time / (successful_count + failed_count):.1f}s",
                }
            )

    # Final summary
    end_time = datetime.now()
    total_time = end_time - start_time

    print("\n" + "=" * 50)
    print("🎉 Scenario Generation Complete!")
    print("📊 Results:")
    print(f"  ✅ Successful: {successful_count}")
    print(f"  ❌ Failed: {failed_count}")
    print(f"  ⏱️  Total time: {total_time}")
    print(f"  📁 Output directory: {output_dir.absolute()}")

    # Display final statistics
    stats = get_scenario_summary_stats(output_dir)
    if "message" not in stats:
        print("\n📈 Dataset Summary:")
        print(f"  Total scenarios: {stats['total_scenarios']}")
        print(f"  Total pharmacies: {stats['total_pharmacies']}")
        print(f"  Total distance: {stats['total_distance_km']:.1f} km")
        print(f"  Total vehicles: {stats['total_vehicles_used']}")
        print(f"  Vehicle range: {stats['min_vehicles']}-{stats['max_vehicles']}")
        print(f"  Avg execution time: {stats['avg_execution_time_sec']:.1f}s")


if __name__ == "__main__":
    main()
