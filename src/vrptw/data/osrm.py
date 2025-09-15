"""OSRM integration for distance matrices and route geometry."""

import pandas as pd
import requests


def get_distance_matrix_osrm(
    depot_lat: float,
    depot_lon: float,
    pharmacies: list[dict[str, str | float]],
    osrm_url: str = "http://127.0.0.1:9001",
    timeout: int = 60,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Get distance and duration matrices from OSRM.

    Args:
        depot_lat: Depot latitude
        depot_lon: Depot longitude
        pharmacies: List of pharmacy dictionaries with 'lat', 'lon' keys
        osrm_url: OSRM server URL
        timeout: Request timeout in seconds

    Returns:
        Tuple of (distance_km_df, duration_sec_df) - DataFrames with depot at index 0

    Raises:
        requests.RequestException: If OSRM request fails
        ValueError: If response format is invalid
    """
    if not pharmacies:
        return pd.DataFrame(), pd.DataFrame()

    # Build coordinate list: depot first, then all pharmacies
    coords = [(depot_lon, depot_lat)]  # OSRM uses lon,lat format
    for pharmacy in pharmacies:
        coords.append((float(pharmacy["lon"]), float(pharmacy["lat"])))

    # Convert to OSRM coordinate string format
    coord_string = ";".join(f"{lon},{lat}" for lon, lat in coords)

    # OSRM table API call
    table_url = f"{osrm_url}/table/v1/driving/{coord_string}"
    params = {"annotations": "distance,duration"}

    try:
        response = requests.get(table_url, params=params, timeout=timeout)
        response.raise_for_status()

        data = response.json()

        if data.get("code") != "Ok":
            raise ValueError(f"OSRM API error: {data.get('message', 'Unknown error')}")

        if "distances" not in data or "durations" not in data:
            raise ValueError("Invalid response format from OSRM table API")

        # Extract distance and duration matrices
        distances = data["distances"]  # meters
        durations = data["durations"]  # seconds

        # Convert to pandas DataFrames and scale distances to km
        n_locations = len(coords)
        distance_km = [
            [distances[i][j] / 1000.0 for j in range(n_locations)] for i in range(n_locations)
        ]
        duration_sec = [[durations[i][j] for j in range(n_locations)] for i in range(n_locations)]

        # Create labeled DataFrames
        labels = ["DEPOT"] + [f"P{i:03d}" for i in range(len(pharmacies))]
        distance_df = pd.DataFrame(distance_km, index=labels, columns=labels)
        duration_df = pd.DataFrame(duration_sec, index=labels, columns=labels)

        return distance_df, duration_df

    except requests.Timeout as e:
        raise requests.RequestException(f"OSRM request timed out after {timeout}s") from e
    except requests.RequestException as e:
        raise requests.RequestException(f"OSRM request failed: {e}") from e
    except (KeyError, TypeError, IndexError) as e:
        raise ValueError(f"Failed to parse OSRM response: {e}") from e


def get_route_geometry(
    osrm_url: str, lat1: float, lon1: float, lat2: float, lon2: float
) -> list[tuple[float, float]]:
    """Get route geometry between two points from OSRM.

    Args:
        osrm_url: OSRM server URL
        lat1: Start latitude
        lon1: Start longitude
        lat2: End latitude
        lon2: End longitude

    Returns:
        List of (lat, lon) coordinate tuples representing the route

    Note:
        Falls back to direct line if OSRM routing fails
    """
    route_url = f"{osrm_url}/route/v1/driving/{lon1},{lat1};{lon2},{lat2}"
    params = {"overview": "full", "geometries": "geojson"}

    try:
        response = requests.get(route_url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        if data.get("code") == "Ok" and "routes" in data and data["routes"]:
            route = data["routes"][0]
            if "geometry" in route and "coordinates" in route["geometry"]:
                # OSRM returns [lon, lat] coordinates, convert to [lat, lon]
                coords = route["geometry"]["coordinates"]
                return [(lat, lon) for lon, lat in coords]

    except (requests.RequestException, KeyError, IndexError):
        # Fall back to direct line if routing fails
        pass

    # Fallback: direct line between points
    return [(lat1, lon1), (lat2, lon2)]
