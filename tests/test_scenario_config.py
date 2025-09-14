"""Tests for VRPTW scenario configuration."""

from src.vrptw.config import VRPConfig
from src.vrptw.scenario_config import (
    ScenarioParams,
    create_vrp_config_for_scenario,
    generate_all_scenarios,
    generate_scenario_id,
    get_scenarios_by_radius,
    get_scenarios_by_time_window,
)


class TestScenarioParams:
    """Tests for ScenarioParams data class."""

    def test_scenario_params_creation(self):
        """Test ScenarioParams instantiation."""
        params = ScenarioParams(
            scenario_id="10_04",
            radius_km=10.0,
            client_tw_hours=4,
            client_tw_start=7 * 3600,
            client_tw_end=11 * 3600,
            depot_tw_start=5 * 3600,
            depot_tw_end=19 * 3600,
        )

        assert params.scenario_id == "10_04"
        assert params.radius_km == 10.0
        assert params.client_tw_hours == 4
        assert params.client_tw_start == 7 * 3600
        assert params.client_tw_end == 11 * 3600
        assert params.depot_tw_start == 5 * 3600
        assert params.depot_tw_end == 19 * 3600


class TestScenarioIdGeneration:
    """Tests for scenario ID generation."""

    def test_generate_scenario_id(self):
        """Test scenario ID generation."""
        assert generate_scenario_id(5, 2) == "05_02"
        assert generate_scenario_id(75, 10) == "75_10"
        assert generate_scenario_id(30, 6) == "30_06"

    def test_generate_scenario_id_formats(self):
        """Test scenario ID formatting with zero padding."""
        assert generate_scenario_id(5, 2) == "05_02"  # Zero padding
        assert generate_scenario_id(15, 10) == "15_10"  # No padding needed


class TestScenarioGeneration:
    """Tests for scenario parameter generation."""

    def test_generate_all_scenarios_count(self):
        """Test that correct number of scenarios are generated."""
        scenarios = generate_all_scenarios()

        # 15 radii (5-75 in steps of 5) × 9 time windows (2-10 hours) = 135 scenarios
        assert len(scenarios) == 135

    def test_generate_all_scenarios_radii(self):
        """Test scenario radii coverage."""
        scenarios = generate_all_scenarios()
        radii = set(s.radius_km for s in scenarios)

        expected_radii = set(range(5, 80, 5))  # 5, 10, 15, ..., 75
        assert radii == expected_radii

    def test_generate_all_scenarios_time_windows(self):
        """Test scenario time window coverage."""
        scenarios = generate_all_scenarios()
        tw_hours = set(s.client_tw_hours for s in scenarios)

        expected_tw_hours = set(range(2, 11))  # 2, 3, 4, ..., 10
        assert tw_hours == expected_tw_hours

    def test_scenario_time_window_consistency(self):
        """Test time window start/end consistency."""
        scenarios = generate_all_scenarios()

        for scenario in scenarios:
            # Client TW always starts at 07:00
            assert scenario.client_tw_start == 7 * 3600

            # Client TW end should be start + hours
            expected_end = scenario.client_tw_start + (scenario.client_tw_hours * 3600)
            assert scenario.client_tw_end == expected_end

            # Depot TW is fixed
            assert scenario.depot_tw_start == 5 * 3600
            assert scenario.depot_tw_end == 19 * 3600

    def test_scenario_id_uniqueness(self):
        """Test that all scenario IDs are unique."""
        scenarios = generate_all_scenarios()
        scenario_ids = [s.scenario_id for s in scenarios]

        assert len(scenario_ids) == len(set(scenario_ids))  # All unique


class TestVRPConfigCreation:
    """Tests for VRP config creation from scenarios."""

    def test_create_vrp_config_for_scenario(self):
        """Test VRP config creation from scenario params."""
        scenario = ScenarioParams(
            scenario_id="20_06",
            radius_km=20.0,
            client_tw_hours=6,
            client_tw_start=7 * 3600,
            client_tw_end=13 * 3600,
            depot_tw_start=5 * 3600,
            depot_tw_end=19 * 3600,
        )

        config = create_vrp_config_for_scenario(scenario)

        # Scenario-specific parameters
        assert config.radius_km == 20.0
        assert config.client_tw_start == 7 * 3600
        assert config.client_tw_end == 13 * 3600
        assert config.depot_tw_start == 5 * 3600
        assert config.depot_tw_end == 19 * 3600

        # Base config parameters should be preserved
        base_config = VRPConfig()
        assert config.center_lat == base_config.center_lat
        assert config.center_lon == base_config.center_lon
        assert config.vehicle_capacity == base_config.vehicle_capacity
        assert config.service_time_sec == base_config.service_time_sec

    def test_create_vrp_config_with_custom_base(self):
        """Test VRP config creation with custom base config."""
        custom_base = VRPConfig(center_lat=50.0, center_lon=10.0, vehicle_capacity=100)

        scenario = ScenarioParams(
            scenario_id="15_04",
            radius_km=15.0,
            client_tw_hours=4,
            client_tw_start=7 * 3600,
            client_tw_end=11 * 3600,
            depot_tw_start=5 * 3600,
            depot_tw_end=19 * 3600,
        )

        config = create_vrp_config_for_scenario(scenario, custom_base)

        # Should use custom base parameters
        assert config.center_lat == 50.0
        assert config.center_lon == 10.0
        assert config.vehicle_capacity == 100

        # But override with scenario-specific parameters
        assert config.radius_km == 15.0
        assert config.client_tw_start == 7 * 3600
        assert config.client_tw_end == 11 * 3600


class TestScenarioFiltering:
    """Tests for scenario filtering functions."""

    def test_get_scenarios_by_radius(self):
        """Test filtering scenarios by radius."""
        scenarios_10km = get_scenarios_by_radius(10)

        # Should have 9 scenarios (one for each time window)
        assert len(scenarios_10km) == 9

        # All should have radius 10km
        for scenario in scenarios_10km:
            assert scenario.radius_km == 10

        # Should cover all time windows
        tw_hours = set(s.client_tw_hours for s in scenarios_10km)
        assert tw_hours == set(range(2, 11))

    def test_get_scenarios_by_time_window(self):
        """Test filtering scenarios by time window length."""
        scenarios_6h = get_scenarios_by_time_window(6)

        # Should have 15 scenarios (one for each radius)
        assert len(scenarios_6h) == 15

        # All should have 6-hour time window
        for scenario in scenarios_6h:
            assert scenario.client_tw_hours == 6

        # Should cover all radii
        radii = set(s.radius_km for s in scenarios_6h)
        assert radii == set(range(5, 80, 5))

    def test_get_scenarios_edge_cases(self):
        """Test edge cases for scenario filtering."""
        # Non-existent radius
        scenarios_invalid = get_scenarios_by_radius(99)
        assert len(scenarios_invalid) == 0

        # Non-existent time window
        scenarios_invalid = get_scenarios_by_time_window(15)
        assert len(scenarios_invalid) == 0
