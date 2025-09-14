"""Overpass API integration for fetching pharmacies from OpenStreetMap."""

import requests


def get_pharmacies_overpass(
    center_lat: float, center_lon: float, radius_km: float, timeout: int = 30
) -> list[dict[str, str | float]]:
    """Fetch pharmacies within radius of center coordinates using Overpass API.

    Args:
        center_lat: Center latitude for search
        center_lon: Center longitude for search
        radius_km: Search radius in kilometers
        timeout: Request timeout in seconds

    Returns:
        List of pharmacy dictionaries with keys: 'name', 'lat', 'lon'

    Raises:
        requests.RequestException: If API request fails
        ValueError: If response format is invalid
    """
    # Convert km to meters for Overpass API
    radius_m = int(radius_km * 1000)

    # Overpass QL query to find pharmacies within radius
    overpass_query = f"""
    [out:json][timeout:{timeout}];
    (
        node["amenity"="pharmacy"](around:{radius_m},{center_lat},{center_lon});
    );
    out center;
    """

    overpass_url = "http://overpass-api.de/api/interpreter"

    try:
        response = requests.post(
            overpass_url,
            data=overpass_query,
            timeout=timeout,
            headers={"User-Agent": "VRPTW-Solver/1.0"},
        )
        response.raise_for_status()

        data = response.json()

        if "elements" not in data:
            raise ValueError("Invalid response format from Overpass API")

        pharmacies = []

        for element in data["elements"]:
            # Handle different element types (node, way, relation)
            if element["type"] == "node":
                lat = element["lat"]
                lon = element["lon"]
            elif element["type"] in ["way", "relation"] and "center" in element:
                lat = element["center"]["lat"]
                lon = element["center"]["lon"]
            else:
                continue  # Skip elements without coordinates

            # Extract pharmacy name (with fallback)
            tags = element.get("tags", {})
            name = tags.get("name", tags.get("brand", f"Pharmacy {element['id']}"))

            pharmacies.append({"name": name, "lat": lat, "lon": lon})

        return pharmacies

    except requests.Timeout:
        raise requests.RequestException(f"Overpass API request timed out after {timeout}s")
    except requests.RequestException as e:
        raise requests.RequestException(f"Overpass API request failed: {e}")
    except (KeyError, TypeError) as e:
        raise ValueError(f"Failed to parse Overpass API response: {e}")
