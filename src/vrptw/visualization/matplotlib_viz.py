"""Matplotlib-based static visualization for VRPTW solutions."""

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt

from ..solver import VRPResult


def generate_colors(n: int) -> list[str]:
    """Generate n visually distinct colors using matplotlib colormap.

    Args:
        n: Number of colors to generate

    Returns:
        List of hex color strings
    """
    if n == 0:
        return []
    if n == 1:
        return ["#1f77b4"]

    # Use matplotlib's tab10 for up to 10 colors, then cycle through viridis
    colors = plt.cm.tab10(range(n)) if n <= 10 else plt.cm.viridis([i / (n - 1) for i in range(n)])

    return [mcolors.to_hex(color) for color in colors]


def plot_vrp_matplotlib(
    result: VRPResult,
    depot_lat: float,
    depot_lon: float,
    output_path: str = "vrp_routes.png",
    show_plot: bool = False,
    figsize: tuple[int, int] = (12, 10),
) -> None:
    """Create static plot of VRPTW solution using matplotlib.

    Args:
        result: VRPTW solution result
        depot_lat: Depot latitude
        depot_lon: Depot longitude
        output_path: Path to save the plot
        show_plot: Whether to display the plot
        figsize: Figure size (width, height) in inches
    """
    if result.status != "OK" or not result.routes:
        print(f"No solution to plot (status: {result.status})")
        return

    plt.figure(figsize=figsize)

    # Generate colors for each vehicle
    colors = generate_colors(result.vehicles_used)

    # Plot depot with better warehouse symbol
    plt.scatter(
        depot_lon,
        depot_lat,
        c="darkred",
        s=300,
        marker="^",
        label="Distribution Center",
        zorder=3,
        edgecolors="black",
        linewidths=2,
    )

    # Track plotted pharmacies to avoid duplicates
    plotted_pharmacies = set()

    # Plot routes for each vehicle
    for i, route in enumerate(result.routes):
        if not route["stops"] or len(route["stops"]) < 2:
            continue

        color = colors[i % len(colors)] if colors else "#1f77b4"

        # Extract coordinates for this route
        route_lons = []
        route_lats = []

        for stop in route["stops"]:
            route_lons.append(stop["lon"])
            route_lats.append(stop["lat"])

            # Plot pharmacy locations with medical cross symbol (skip depot)
            if not stop["is_depot"]:
                pharmacy_key = (stop["lat"], stop["lon"])
                if pharmacy_key not in plotted_pharmacies:
                    plt.scatter(
                        stop["lon"],
                        stop["lat"],
                        c="mediumblue",
                        s=80,
                        marker="+",
                        alpha=0.8,
                        zorder=2,
                        linewidths=3,
                    )
                    plotted_pharmacies.add(pharmacy_key)

        # Plot route line
        plt.plot(
            route_lons,
            route_lats,
            color=color,
            linewidth=2,
            alpha=0.8,
            label=f"Vehicle {route['vehicle']} ({len(route['stops']) - 2} stops)",
        )

        # Add arrows to show direction
        for j in range(len(route_lons) - 1):
            dx = route_lons[j + 1] - route_lons[j]
            dy = route_lats[j + 1] - route_lats[j]
            plt.arrow(
                route_lons[j],
                route_lats[j],
                dx * 0.3,
                dy * 0.3,
                head_width=0.001,
                head_length=0.001,
                fc=color,
                ec=color,
                alpha=0.6,
            )

    # Formatting
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.title(
        f"VRPTW Solution - {result.vehicles_used} Vehicles, "
        f"{result.total_distance_km:.1f}km, "
        f"{result.total_time_sec / 3600:.1f}h"
    )

    # Legend
    plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left")

    # Grid and equal aspect ratio
    plt.grid(True, alpha=0.3)
    plt.axis("equal")

    # Adjust layout to prevent legend cutoff
    plt.tight_layout()

    # Save plot
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"Static plot saved to: {output_path}")

    if show_plot:
        plt.show()
    else:
        plt.close()


def plot_solution_overview(result: VRPResult, output_path: str = "solution_overview.png") -> None:
    """Create a summary plot with solution statistics.

    Args:
        result: VRPTW solution result
        output_path: Path to save the overview plot
    """
    if result.status != "OK":
        return

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 8))

    # Vehicle utilization
    vehicle_loads = [route["load"] for route in result.routes if route["load"] > 0]
    ax1.bar(range(len(vehicle_loads)), vehicle_loads)
    ax1.set_title("Vehicle Loads")
    ax1.set_xlabel("Vehicle")
    ax1.set_ylabel("Load (pharmacies)")

    # Stops per vehicle
    vehicle_stops = [len(route["stops"]) - 2 for route in result.routes if len(route["stops"]) > 2]
    ax2.bar(range(len(vehicle_stops)), vehicle_stops)
    ax2.set_title("Stops per Vehicle")
    ax2.set_xlabel("Vehicle")
    ax2.set_ylabel("Number of Stops")

    # Route duration histogram
    route_times = []
    for route in result.routes:
        if len(route["stops"]) > 2:
            start_time = route["stops"][0]["arrival_time"]
            end_time = route["stops"][-1]["arrival_time"]
            duration_hours = (end_time - start_time) / 3600
            route_times.append(duration_hours)

    ax3.hist(route_times, bins=max(5, len(route_times) // 2), alpha=0.7)
    ax3.set_title("Route Duration Distribution")
    ax3.set_xlabel("Duration (hours)")
    ax3.set_ylabel("Number of Routes")

    # Summary statistics
    total_pharmacies = sum(len(r["stops"]) - 2 for r in result.routes)
    stats_text = f"""Solution Summary:
Vehicles Used: {result.vehicles_used}
Total Pharmacies: {total_pharmacies}
Total Distance: {result.total_distance_km:.1f} km
Total Time: {result.total_time_sec / 3600:.1f} hours
Avg Stops/Vehicle: {total_pharmacies / result.vehicles_used:.1f}"""

    ax4.text(
        0.1,
        0.5,
        stats_text,
        transform=ax4.transAxes,
        fontsize=11,
        verticalalignment="center",
        bbox=dict(boxstyle="round", facecolor="lightgray"),
    )
    ax4.set_xlim(0, 1)
    ax4.set_ylim(0, 1)
    ax4.axis("off")
    ax4.set_title("Statistics")

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"Solution overview saved to: {output_path}")
    plt.close()
