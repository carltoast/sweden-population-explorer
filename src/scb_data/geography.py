"""Spatial helpers: distance, point-in-polygon, and radius search."""

import math

EARTH_RADIUS_KM = 6371.0


def haversine_distance_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Compute the great-circle distance between two points.

    Args:
        lat1: Latitude of the first point, in degrees.
        lon1: Longitude of the first point, in degrees.
        lat2: Latitude of the second point, in degrees.
        lon2: Longitude of the second point, in degrees.

    Returns:
        The distance between the two points, in kilometers.
    """
    lat1_r = math.radians(lat1)
    lon1_r = math.radians(lon1)
    lat2_r = math.radians(lat2)
    lon2_r = math.radians(lon2)

    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    )

    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def _point_in_ring(lon: float, lat: float, ring: list[list[float]]) -> bool:
    """Run a ray-casting point-in-polygon test against a single ring.

    Args:
        lon: Longitude of the point to test, in degrees.
        lat: Latitude of the point to test, in degrees.
        ring: A single linear ring, as a list of [lon, lat] vertices
            (GeoJSON coordinate order).

    Returns:
        True if the point falls inside the ring.
    """
    inside = False
    j = len(ring) - 1

    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]

        # yi != yj is guaranteed here, so this never divides by zero.
        if (yi > lat) != (yj > lat):
            x_at_lat = (xj - xi) * (lat - yi) / (yj - yi) + xi

            if lon < x_at_lat:
                inside = not inside

        j = i

    return inside


def point_in_geometry(
    latitude: float,
    longitude: float,
    geometry: dict,
) -> bool:
    """Check whether a point falls inside a Polygon/MultiPolygon geometry.

    Holes (interior rings) are respected: a point inside a hole is not
    considered inside the polygon.

    Args:
        latitude: Latitude of the point to test, in degrees.
        longitude: Longitude of the point to test, in degrees.
        geometry: A GeoJSON geometry object. Any type other than Polygon
            or MultiPolygon is treated as not containing the point.

    Returns:
        True if the point falls inside the geometry.
    """
    if geometry["type"] == "Polygon":
        polygons = [geometry["coordinates"]]
    elif geometry["type"] == "MultiPolygon":
        polygons = geometry["coordinates"]
    else:
        return False

    for polygon in polygons:
        exterior_ring, *holes = polygon

        if not _point_in_ring(longitude, latitude, exterior_ring):
            continue

        if any(_point_in_ring(longitude, latitude, hole) for hole in holes):
            continue

        return True

    return False


def find_municipalities_within_radius(
    latitude: float,
    longitude: float,
    radius_km: float,
    geojson: dict,
) -> list[dict]:
    """Find municipalities within radius_km of (latitude, longitude).

    Uses each municipality's `geo_point_2d` property (its representative
    point, as supplied in the GeoJSON) rather than true polygon/circle
    intersection. This is an approximation: for very large municipalities,
    the representative point can be far from where the radius actually
    touches the municipality's boundary. To compensate, the municipality
    whose actual polygon contains (latitude, longitude) is always included,
    even if its representative point falls outside radius_km - otherwise a
    small radius could exclude the very municipality the point is in.

    Args:
        latitude: Latitude of the selected point, in degrees.
        longitude: Longitude of the selected point, in degrees.
        radius_km: Search radius, in kilometers.
        geojson: A GeoJSON FeatureCollection of municipalities, with an
            "id" (region code), "kom_namn" (name), and "geo_point_2d"
            ([lat, lon]) property per feature.

    Returns:
        One dict per matching municipality, with region_code, region,
        distance_km (to its representative point), and contains_point
        (whether its actual polygon contains the selected point), sorted
        by distance_km ascending.
    """
    results = []

    for feature in geojson["features"]:
        properties = feature["properties"]
        centroid_lat, centroid_lon = properties["geo_point_2d"]

        distance_km = haversine_distance_km(
            latitude, longitude, centroid_lat, centroid_lon
        )

        contains_point = point_in_geometry(
            latitude, longitude, feature["geometry"]
        )

        if distance_km <= radius_km or contains_point:
            results.append(
                {
                    "region_code": properties["id"],
                    "region": properties["kom_namn"],
                    "distance_km": distance_km,
                    "contains_point": contains_point,
                }
            )

    results.sort(key=lambda result: result["distance_km"])

    return results
