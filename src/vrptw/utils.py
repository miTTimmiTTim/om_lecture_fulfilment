"""Utility functions for VRPTW solver."""

from .solver import VRPResult


def _fmt_time(seconds: int) -> str:
    """Format seconds to HH:MM string."""
    h = seconds // 3600
    m = (seconds % 3600) // 60
    return f"{h:02d}:{m:02d}"


def summarize_result(result: VRPResult) -> None:
    """Print a summary of the VRPTW solution.

    Args:
        result: VRPTW solution result
    """
    if result.status != "OK":
        print(f"Status: {result.status}")
        return

    total_clients = sum(len(r["stops"]) - 2 for r in result.routes)  # exclude depot endpoints
    avg_stops = total_clients / result.vehicles_used if result.vehicles_used else 0

    print("=== VRPTW SUMMARY ===")
    print(f"Vehicles used: {result.vehicles_used}")
    print(f"Total clients served: {total_clients}")
    print(f"Avg stops/vehicle: {avg_stops:.1f}")
    print(f"Total travel distance (approx km): {result.total_distance_km:.1f}")
    print(f"Total time (h): {result.total_time_sec / 3600:.2f}")

    # Per vehicle details
    for r in result.routes:
        stops = len(r["stops"]) - 2
        if stops <= 0:
            continue
        start_time = r["stops"][0]["arrival_time"]  # depot departure
        first_time = r["stops"][1]["arrival_time"] if stops else 0  # first client arrival
        last_time = r["stops"][-2]["arrival_time"] if stops else 0  # last client arrival
        return_time = r["stops"][-1]["arrival_time"]  # arrival back at depot

        print(
            f" V{r['vehicle']:02d}: {stops} stops, start {_fmt_time(start_time)}, "
            f"first {_fmt_time(first_time)}, last {_fmt_time(last_time)}, "
            f"return {_fmt_time(return_time)}"
        )
