"""Tests for configuration module."""

from src.vrptw.config import VRPConfig


def test_vrp_config_defaults():
    """Test VRPConfig default values."""
    config = VRPConfig()

    # Check geographic defaults
    assert config.center_lat == 49.504896
    assert config.center_lon == 11.015822
    assert config.radius_km == 50
    assert config.osrm_url == "http://127.0.0.1:9001"

    # Check time windows
    assert config.client_tw_start == 7 * 3600  # 07:00
    assert config.client_tw_end == 9 * 3600  # 09:00
    assert config.depot_tw_start == 5 * 3600  # 05:00
    assert config.depot_tw_end == 19 * 3600  # 19:00

    # Check vehicle settings
    assert config.service_time_sec == 600
    assert config.vehicle_capacity == 50
    assert config.vehicle_fixed_cost == 5000

    # Check solver settings
    assert config.initial_vehicle_count == 50
    assert config.auto_increase_vehicles is True
    assert config.time_limit_sec == 20


def test_vrp_config_customization():
    """Test VRPConfig customization."""
    config = VRPConfig(
        center_lat=50.0,
        center_lon=12.0,
        radius_km=25,
        service_time_sec=300,
    )

    assert config.center_lat == 50.0
    assert config.center_lon == 12.0
    assert config.radius_km == 25
    assert config.service_time_sec == 300

    # Check that other defaults are preserved
    assert config.vehicle_capacity == 50
