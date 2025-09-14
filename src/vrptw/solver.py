"""OR-Tools VRPTW solver implementation."""

from dataclasses import dataclass
from typing import Any

import pandas as pd

from .data import get_distance_matrix_osrm, get_pharmacies_overpass

try:
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2
except ImportError:
    pywrapcp = None
    routing_enums_pb2 = None


@dataclass
class VRPResult:
    """Container for VRPTW solution results."""

    routes: list[dict[str, Any]]
    total_distance_km: float
    total_time_sec: int
    vehicles_used: int
    status: str


def _require_ortools():
    """Check if OR-Tools is available."""
    if pywrapcp is None or routing_enums_pb2 is None:
        raise ImportError("OR-Tools not available. Install with: uv add ortools")


def prepare_matrices(
    depot_lat: float,
    depot_lon: float,
    radius_km: float,
    osrm_url: str = "http://127.0.0.1:9001",
) -> tuple[pd.DataFrame, pd.DataFrame, list[dict]]:
    """Fetch pharmacies & OSRM matrices for a given radius around the depot.

    Args:
        depot_lat: Depot latitude
        depot_lon: Depot longitude
        radius_km: Search radius in kilometers
        osrm_url: OSRM server URL

    Returns:
        Tuple of (distance_km_df, duration_sec_df, pharmacies_list)
    """
    pharmacies = get_pharmacies_overpass(depot_lat, depot_lon, radius_km)
    if not pharmacies:
        return pd.DataFrame(), pd.DataFrame(), []

    dist_df, dur_df = get_distance_matrix_osrm(depot_lat, depot_lon, pharmacies, osrm_url=osrm_url)
    return dist_df, dur_df, pharmacies


def solve_vrptw(
    depot_lat: float,
    depot_lon: float,
    radius_km: float,
    vehicle_count: int | None,
    vehicle_capacity: int,
    service_time_sec: int,
    vehicle_fixed_cost: int,
    client_tw: tuple[int, int],
    depot_tw: tuple[int, int] | None,
    osrm_url: str,
    time_limit_sec: int,
    auto_increase_vehicles: bool,
) -> VRPResult:
    """Solve VRPTW using OR-Tools.

    Strategy: use OSRM durations as travel time, append service time at origin node
    inside the time callback so arrival times represent service start times.

    Args:
        depot_lat: Depot latitude
        depot_lon: Depot longitude
        radius_km: Search radius in kilometers
        vehicle_count: Number of vehicles (None for auto calculation)
        vehicle_capacity: Vehicle capacity
        service_time_sec: Service time per stop in seconds
        vehicle_fixed_cost: Fixed cost per vehicle
        client_tw: Client time window (start, end) in seconds
        depot_tw: Depot time window (start, end) in seconds
        osrm_url: OSRM server URL
        time_limit_sec: Solver time limit
        auto_increase_vehicles: Whether to increase vehicles if infeasible

    Returns:
        VRPResult with routes and statistics
    """
    _require_ortools()

    dist_df, dur_df, pharmacies = prepare_matrices(
        depot_lat, depot_lon, radius_km, osrm_url=osrm_url
    )
    if dur_df.empty:
        return VRPResult([], 0.0, 0, 0, status="NO_DATA")

    n_clients = len(pharmacies)
    # Build data model indices: 0 = depot, 1..n = clients
    time_matrix = dur_df.values  # seconds, float
    distance_matrix = dist_df.values  # km, float

    # Convert to int seconds (round) to satisfy OR-Tools integer requirement
    time_matrix_int = [[int(round(v)) for v in row] for row in time_matrix]

    # Demands: 0 at depot, 1 per pharmacy
    demands = [0] + [1] * n_clients
    service_times = [0] + [service_time_sec] * n_clients

    # Time windows: depot can have its own window; clients share client_tw
    if depot_tw is None:
        depot_tw = client_tw
    depot_start, depot_end = depot_tw
    client_start, client_end = client_tw
    time_windows = [depot_tw] + [(client_start, client_end)] * n_clients

    # If vehicle_count unspecified, heuristic lower bound via total service time / window span
    if vehicle_count is None:
        window_span = max(1, client_end - client_start)
        lower_bound = (n_clients * service_time_sec) / window_span
        vehicle_count = max(1, int(round(lower_bound + 2)))  # small buffer

    def try_solve(v_count: int) -> tuple[Any | None, Any | None, Any | None]:
        """Try to solve with given vehicle count."""
        manager_loc = pywrapcp.RoutingIndexManager(len(time_matrix_int), v_count, 0)
        routing_loc = pywrapcp.RoutingModel(manager_loc)

        def time_callback(from_index: int, to_index: int) -> int:
            from_node = manager_loc.IndexToNode(from_index)
            to_node = manager_loc.IndexToNode(to_index)
            return time_matrix_int[from_node][to_node] + service_times[from_node]

        transit_idx = routing_loc.RegisterTransitCallback(time_callback)
        routing_loc.SetArcCostEvaluatorOfAllVehicles(transit_idx)

        def demand_callback(from_index: int) -> int:
            node = manager_loc.IndexToNode(from_index)
            return demands[node]

        demand_idx = routing_loc.RegisterUnaryTransitCallback(demand_callback)
        routing_loc.AddDimensionWithVehicleCapacity(
            demand_idx, 0, [vehicle_capacity] * v_count, True, "Capacity"
        )

        routing_loc.AddDimension(
            transit_idx,
            0,
            (max(depot_end, client_end) - min(depot_start, client_start))
            + service_time_sec * n_clients,
            False,
            "Time",
        )

        time_dim_loc = routing_loc.GetDimensionOrDie("Time")
        for node, (start, end) in enumerate(time_windows):
            index = manager_loc.NodeToIndex(node)
            time_dim_loc.CumulVar(index).SetRange(start, end)

        for v in range(v_count):
            start_index = routing_loc.Start(v)
            end_index = routing_loc.End(v)
            time_dim_loc.CumulVar(start_index).SetRange(depot_start, depot_end)
            time_dim_loc.CumulVar(end_index).SetRange(depot_start, depot_end)

        routing_loc.SetFixedCostOfAllVehicles(vehicle_fixed_cost)

        search_params = pywrapcp.DefaultRoutingSearchParameters()
        search_params.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_params.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_params.time_limit.FromSeconds(time_limit_sec)

        sol = routing_loc.SolveWithParameters(search_params)
        return sol, routing_loc, manager_loc

    solution, routing, manager = try_solve(vehicle_count)

    if not solution and auto_increase_vehicles:
        # escalate up to one vehicle per client (worst-case) or until solution found
        for v in range(vehicle_count + 1, n_clients + 1, 10):
            print(f"Trying with {v} vehicles...")
            solution, routing, manager = try_solve(v)
            if solution:
                vehicle_count = v
                break

    if not solution:
        return VRPResult([], 0.0, 0, 0, status="NO_SOLUTION")

    # Retrieve time dimension from the chosen routing model
    assert routing is not None and manager is not None
    time_dimension = routing.GetDimensionOrDie("Time")

    routes: list[dict[str, Any]] = []
    total_distance_km = 0.0
    total_time_sec = 0
    vehicles_used = 0

    for v in range(vehicle_count):
        index = routing.Start(v)
        if routing.IsEnd(solution.Value(routing.NextVar(index))):
            continue  # unused vehicle

        vehicles_used += 1
        route_nodes = []
        route_load = 0

        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            t_cumul = solution.Value(time_dimension.CumulVar(index))
            route_nodes.append(
                {
                    "node": node,
                    "is_depot": node == 0,
                    "arrival_time": t_cumul,
                    "name": "DEPOT" if node == 0 else pharmacies[node - 1]["name"],
                    "lat": depot_lat if node == 0 else pharmacies[node - 1]["lat"],
                    "lon": depot_lon if node == 0 else pharmacies[node - 1]["lon"],
                }
            )
            route_load += demands[node]
            prev_index = index
            index = solution.Value(routing.NextVar(index))

            if not routing.IsEnd(index):
                from_node = manager.IndexToNode(prev_index)
                to_node = manager.IndexToNode(index)
                total_distance_km += distance_matrix[from_node][to_node]
                total_time_sec += time_matrix_int[from_node][to_node] + service_times[from_node]

        # add depot end
        node = manager.IndexToNode(index)
        t_cumul = solution.Value(time_dimension.CumulVar(index))
        route_nodes.append(
            {
                "node": node,
                "is_depot": True,
                "arrival_time": t_cumul,
                "name": "DEPOT",
                "lat": depot_lat,
                "lon": depot_lon,
            }
        )
        routes.append({"vehicle": v, "stops": route_nodes, "load": route_load})

    return VRPResult(
        routes, float(total_distance_km), int(total_time_sec), vehicles_used, status="OK"
    )
