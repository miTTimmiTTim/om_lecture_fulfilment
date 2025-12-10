"""Overpass API integration for fetching venues from OpenStreetMap."""

import requests


def get_venues_overpass(
    center_lat: float, center_lon: float, radius_km: float, timeout: int = 60
) -> list[dict[str, str | float]]:
    """Fetch bars, pubs, and biergärten within radius of center coordinates using Overpass API.

    Args:
        center_lat: Center latitude for search
        center_lon: Center longitude for search
        radius_km: Search radius in kilometers
        timeout: Request timeout in seconds

    Returns:
        List of venue dictionaries with keys: 'name', 'lat', 'lon', 'type'

    Raises:
        requests.RequestException: If API request fails
        ValueError: If response format is invalid
    """
    # Convert km to meters for Overpass API
    radius_m = int(radius_km * 1000)

    # Overpass QL query to find bars, pubs, and biergärten within radius
    overpass_query = f"""
    [out:json][timeout:{timeout}];
    (
        node["amenity"="bar"](around:{radius_m},{center_lat},{center_lon});
        node["amenity"="pub"](around:{radius_m},{center_lat},{center_lon});
        node["amenity"="biergarten"](around:{radius_m},{center_lat},{center_lon});
    );
    out center;
    """

    overpass_urls = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    ]

    last_error = None
    for overpass_url in overpass_urls:
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

            venues = []

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

                # Extract venue info
                tags = element.get("tags", {})
                name = tags.get("name")

                # Skip venues without names
                if not name:
                    continue

                venue_type = tags.get("amenity", "unknown")

                venues.append({"name": name, "lat": lat, "lon": lon, "type": venue_type})

            return venues

        except (requests.Timeout, requests.RequestException) as e:
            last_error = e
            continue  # Try next mirror

    # All mirrors failed
    raise requests.RequestException(f"All Overpass mirrors failed. Last error: {last_error}")


# Keep backward compatibility alias
def get_pharmacies_overpass(
    center_lat: float, center_lon: float, radius_km: float, timeout: int = 60
) -> list[dict[str, str | float]]:
    """Alias for get_venues_overpass for backward compatibility with scenario_generator."""
    return get_venues_overpass(center_lat, center_lon, radius_km, timeout)
