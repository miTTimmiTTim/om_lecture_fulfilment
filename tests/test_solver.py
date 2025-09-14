"""Tests for VRPTW solver."""

from unittest.mock import MagicMock, patch

import pytest

from src.vrptw.solver import VRPResult, _require_ortools


class TestVRPResult:
    """Tests for VRPResult data container."""

    def test_vrp_result_creation(self):
        """Test VRPResult instantiation."""
        result = VRPResult(
            routes=[{"vehicle": 0, "stops": []}],
            total_distance_km=100.5,
            total_time_sec=3600,
            vehicles_used=2,
            status="OK",
        )

        assert len(result.routes) == 1
        assert result.total_distance_km == 100.5
        assert result.total_time_sec == 3600
        assert result.vehicles_used == 2
        assert result.status == "OK"


class TestORToolsRequirement:
    """Tests for OR-Tools requirement checking."""

    @patch("src.vrptw.solver.pywrapcp", None)
    @patch("src.vrptw.solver.routing_enums_pb2", None)
    def test_require_ortools_missing(self):
        """Test OR-Tools requirement when not available."""
        with pytest.raises(ImportError, match="OR-Tools not available"):
            _require_ortools()

    @patch("src.vrptw.solver.pywrapcp", MagicMock())
    @patch("src.vrptw.solver.routing_enums_pb2", MagicMock())
    def test_require_ortools_available(self):
        """Test OR-Tools requirement when available."""
        # Should not raise
        _require_ortools()
