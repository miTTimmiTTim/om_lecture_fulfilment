"""Tests for VRPTW scenario storage functionality."""

import json
import tempfile
from pathlib import Path

import polars as pl
import pytest

from src.vrptw.scenario_config import ScenarioParams
from src.vrptw.scenario_storage import (
    calculate_pharmacy_distances,
    get_scenario_summary_stats,
    initialize_scenario_data_directory,
    load_completed_scenarios,
    mark_scenario_completed,
    store_pharmacies_data,
    store_scenario_result,
)
from src.vrptw.solver import VRPResult


class TestPharmacyDistanceCalculation:
    """Tests for pharmacy distance calculations with Polars."""

    def test_calculate_pharmacy_distances(self):
        """Test pharmacy distance calculation."""
        pharmacies = [
            {"id": "1", "name": "Pharmacy A", "lat": 49.517037, "lon": 11.088860},
            {"id": "2", "name": "Pharmacy B", "lat": 49.496891, "lon": 11.003860},
        ]

        center_lat, center_lon = 49.517037, 11.088860

        df = calculate_pharmacy_distances(pharmacies, center_lat, center_lon)

        # Check DataFrame structure
        assert isinstance(df, pl.DataFrame)
        assert len(df) == 2
        assert "distance_from_center_km" in df.columns
        assert "id" in df.columns
        assert "name" in df.columns
        assert "lat" in df.columns
        assert "lon" in df.columns

        # Check distance calculations
        distances = df["distance_from_center_km"].to_list()
        assert distances[0] == pytest.approx(0.0, abs=0.1)  # Same location
        assert distances[1] > 0  # Different location
        assert distances[1] < 10  # Reasonable distance for nearby location

    def test_calculate_pharmacy_distances_empty(self):
        """Test distance calculation with empty pharmacy list."""
        df = calculate_pharmacy_distances([], 49.5, 11.0)

        assert isinstance(df, pl.DataFrame)
        assert len(df) == 0


class TestScenarioDataDirectory:
    """Tests for scenario data directory management."""

    def test_initialize_scenario_data_directory(self):
        """Test scenario data directory initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "test_scenarios"

            initialize_scenario_data_directory(output_dir)

            # Check directory structure
            assert output_dir.exists()
            assert (output_dir / "routes").exists()
            assert (output_dir / "metadata.json").exists()

            # Check metadata content
            with open(output_dir / "metadata.json") as f:
                metadata = json.load(f)

            assert "dataset" in metadata
            assert "total_scenarios" in metadata
            assert metadata["total_scenarios"] == 135
            assert "parameters" in metadata


class TestPharmacyDataStorage:
    """Tests for pharmacy data storage."""

    def test_store_pharmacies_data(self):
        """Test storing pharmacy data as parquet."""
        pharmacies_df = pl.DataFrame(
            {
                "id": ["1", "2"],
                "name": ["Pharmacy A", "Pharmacy B"],
                "lat": [49.5, 49.6],
                "lon": [11.0, 11.1],
                "distance_from_center_km": [0.5, 1.2],
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            store_pharmacies_data(pharmacies_df, output_dir)

            # Check file exists
            parquet_file = output_dir / "pharmacies.parquet"
            assert parquet_file.exists()

            # Check data integrity
            loaded_df = pl.read_parquet(parquet_file)
            assert loaded_df.equals(pharmacies_df)


class TestScenarioResultStorage:
    """Tests for scenario result storage."""

    def test_store_scenario_result_new_file(self):
        """Test storing scenario result when CSV doesn't exist."""
        scenario = ScenarioParams(
            scenario_id="10_04_06",
            radius_km=10.0,
            client_tw_hours=4,
            client_tw_start=7 * 3600,
            client_tw_end=11 * 3600,
            depot_tw_start=5 * 3600,
            depot_tw_end=19 * 3600,
            service_time_sec=360,
        )

        result = VRPResult(
            routes=[{"vehicle": 1, "stops": [], "load": 5}],
            total_distance_km=100.5,
            total_time_sec=3600,
            vehicles_used=1,
            status="OK",
        )

        route_geometries = {
            "routes": [],
            "total_distance_km": 100.5,
            "total_time_sec": 3600,
            "vehicles_used": 1,
            "status": "OK",
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            (output_dir / "routes").mkdir()

            store_scenario_result(
                scenario=scenario,
                result=result,
                route_geometries=route_geometries,
                pharmacies_count=25,
                execution_time_sec=45.2,
                output_dir=output_dir,
            )

            # Check CSV file
            csv_file = output_dir / "scenarios.csv"
            assert csv_file.exists()

            df = pl.read_csv(csv_file)
            assert len(df) == 1
            assert df["scenario_id"][0] == "10_04_06"
            assert df["vehicles_used"][0] == 1
            assert df["pharmacies_count"][0] == 25

            # Check JSON route file
            route_file = output_dir / "routes" / "scenario_10_04_06.json"
            assert route_file.exists()

            with open(route_file) as f:
                route_data = json.load(f)

            assert route_data["scenario_id"] == "10_04_06"
            assert route_data["solution"]["vehicles_used"] == 1


class TestCompletedScenariosTracking:
    """Tests for completed scenarios checkpoint system."""

    def test_load_completed_scenarios_empty(self):
        """Test loading completed scenarios when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            completed = load_completed_scenarios(output_dir)
            assert completed == set()

    def test_mark_and_load_completed_scenarios(self):
        """Test marking and loading completed scenarios."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # Mark some scenarios as completed
            mark_scenario_completed("05_02", output_dir)
            mark_scenario_completed("10_04", output_dir)
            mark_scenario_completed("15_06", output_dir)

            # Load completed scenarios
            completed = load_completed_scenarios(output_dir)
            assert completed == {"05_02", "10_04", "15_06"}

    def test_completed_file_format(self):
        """Test completed scenarios file format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            mark_scenario_completed("20_08", output_dir)

            completed_file = output_dir / "completed.txt"
            assert completed_file.exists()

            with open(completed_file) as f:
                content = f.read().strip()

            assert content == "20_08"


class TestScenarioSummaryStats:
    """Tests for scenario summary statistics."""

    def test_get_scenario_summary_stats_empty(self):
        """Test summary stats when no scenarios completed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            stats = get_scenario_summary_stats(output_dir)
            assert "message" in stats
            assert "No scenarios completed" in stats["message"]

    def test_get_scenario_summary_stats(self):
        """Test summary stats calculation."""
        # Create test CSV file
        test_data = pl.DataFrame(
            {
                "scenario_id": ["05_02", "10_04", "15_06"],
                "radius_km": [5, 10, 15],
                "client_tw_hours": [2, 4, 6],
                "pharmacies_count": [20, 50, 80],
                "vehicles_used": [2, 5, 8],
                "total_distance_km": [100.0, 250.0, 400.0],
                "total_time_sec": [3600, 7200, 10800],
                "execution_time_sec": [30.0, 45.0, 60.0],
                "status": ["OK", "OK", "OK"],
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            csv_file = output_dir / "scenarios.csv"
            test_data.write_csv(csv_file)

            stats = get_scenario_summary_stats(output_dir)

            assert stats["total_scenarios"] == 3
            assert stats["successful_scenarios"] == 3
            assert stats["failed_scenarios"] == 0
            assert stats["total_pharmacies"] == 150  # 20 + 50 + 80
            assert stats["total_distance_km"] == 750.0  # 100 + 250 + 400
            assert stats["total_vehicles_used"] == 15  # 2 + 5 + 8
            assert stats["min_vehicles"] == 2
            assert stats["max_vehicles"] == 8
            assert stats["radius_range"] == "5-15 km"

    def test_get_scenario_summary_stats_with_failures(self):
        """Test summary stats with failed scenarios."""
        test_data = pl.DataFrame(
            {
                "scenario_id": ["05_02", "10_04"],
                "radius_km": [5, 10],
                "client_tw_hours": [2, 4],
                "pharmacies_count": [20, 50],
                "vehicles_used": [2, 0],  # Second scenario failed
                "total_distance_km": [100.0, 0.0],
                "total_time_sec": [3600, 0],
                "execution_time_sec": [30.0, 15.0],
                "status": ["OK", "INFEASIBLE"],
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            csv_file = output_dir / "scenarios.csv"
            test_data.write_csv(csv_file)

            stats = get_scenario_summary_stats(output_dir)

            assert stats["total_scenarios"] == 2
            assert stats["successful_scenarios"] == 1
            assert stats["failed_scenarios"] == 1
            # Should only count successful scenarios in distance/vehicle stats
            assert stats["total_distance_km"] == 100.0
            assert stats["total_vehicles_used"] == 2
