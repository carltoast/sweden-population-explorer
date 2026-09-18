"""Tests for scb_data.geography: distance, point-in-polygon, radius search."""

import pytest

from scb_data.geography import (
    find_counties_within_radius,
    find_municipalities_within_radius,
    haversine_distance_km,
    point_in_geometry,
)

VASTRA_GOTALAND_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "id": "1480",
                "kom_namn": "Göteborg",
                "lan_code": "14",
                "geo_point_2d": [57.7089, 11.9746],
            },
            "geometry": {
                "type": "Point",
                "coordinates": [11.9746, 57.7089],
            },
        },
        {
            "type": "Feature",
            "properties": {
                "id": "1401",
                "kom_namn": "Härryda",
                "lan_code": "14",
                # Far outside any radius used below, to prove county
                # grouping includes it via lan_code, not distance.
                "geo_point_2d": [50, 50],
            },
            "geometry": {"type": "Point", "coordinates": [50, 50]},
        },
        {
            "type": "Feature",
            "properties": {
                "id": "0180",
                "kom_namn": "Stockholm",
                "lan_code": "01",
                "geo_point_2d": [59.3293, 18.0686],
            },
            "geometry": {
                "type": "Point",
                "coordinates": [18.0686, 59.3293],
            },
        },
    ],
}


def test_haversine_distance_km_same_point_is_zero():
    assert haversine_distance_km(57.7089, 11.9746, 57.7089, 11.9746) == 0


def test_haversine_distance_km_one_degree_latitude_is_about_111_km():
    distance = haversine_distance_km(0, 0, 1, 0)

    assert distance == pytest.approx(111.19, abs=0.1)


def test_find_municipalities_within_radius_filters_by_distance():
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "id": "1480",
                    "kom_namn": "Göteborg",
                    "geo_point_2d": [57.7089, 11.9746],
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [11.9746, 57.7089],
                },
            },
            {
                "type": "Feature",
                "properties": {
                    "id": "1401",
                    "kom_namn": "Härryda",
                    "geo_point_2d": [57.65, 12.15],
                },
                "geometry": {"type": "Point", "coordinates": [12.15, 57.65]},
            },
            {
                "type": "Feature",
                "properties": {
                    "id": "0180",
                    "kom_namn": "Stockholm",
                    "geo_point_2d": [59.3293, 18.0686],
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [18.0686, 59.3293],
                },
            },
        ],
    }

    results = find_municipalities_within_radius(
        latitude=57.7089,
        longitude=11.9746,
        radius_km=30,
        geojson=geojson,
    )

    assert [result["region_code"] for result in results] == ["1480", "1401"]


def test_find_municipalities_within_radius_sorts_nearest_first():
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "id": "1401",
                    "kom_namn": "Härryda",
                    "geo_point_2d": [57.65, 12.15],
                },
                "geometry": {"type": "Point", "coordinates": [12.15, 57.65]},
            },
            {
                "type": "Feature",
                "properties": {
                    "id": "1480",
                    "kom_namn": "Göteborg",
                    "geo_point_2d": [57.7089, 11.9746],
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [11.9746, 57.7089],
                },
            },
        ],
    }

    results = find_municipalities_within_radius(
        latitude=57.7089,
        longitude=11.9746,
        radius_km=30,
        geojson=geojson,
    )

    assert [result["region_code"] for result in results] == ["1480", "1401"]


def test_find_municipalities_within_radius_includes_distance():
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "id": "1480",
                    "kom_namn": "Göteborg",
                    "geo_point_2d": [57.7089, 11.9746],
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [11.9746, 57.7089],
                },
            }
        ],
    }

    results = find_municipalities_within_radius(
        latitude=57.7089,
        longitude=11.9746,
        radius_km=30,
        geojson=geojson,
    )

    assert results[0]["distance_km"] == pytest.approx(0)


def test_find_municipalities_within_radius_returns_empty_when_none_in_range():
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "id": "0180",
                    "kom_namn": "Stockholm",
                    "geo_point_2d": [59.3293, 18.0686],
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [18.0686, 59.3293],
                },
            }
        ],
    }

    results = find_municipalities_within_radius(
        latitude=57.7089,
        longitude=11.9746,
        radius_km=30,
        geojson=geojson,
    )

    assert results == []


def test_find_municipalities_within_radius_includes_far_containing():
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "id": "9999",
                    "kom_namn": "Big Municipality",
                    # Representative point is far from the point below.
                    "geo_point_2d": [50, 50],
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
                    ],
                },
            }
        ],
    }

    results = find_municipalities_within_radius(
        latitude=5,
        longitude=5,
        radius_km=1,
        geojson=geojson,
    )

    assert len(results) == 1
    assert results[0]["region_code"] == "9999"
    assert results[0]["contains_point"] is True


def test_find_municipalities_within_radius_sets_contains_point_false():
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "id": "1480",
                    "kom_namn": "Göteborg",
                    "geo_point_2d": [57.7089, 11.9746],
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [11.9746, 57.7089],
                },
            }
        ],
    }

    results = find_municipalities_within_radius(
        latitude=57.7089,
        longitude=11.9746,
        radius_km=30,
        geojson=geojson,
    )

    assert results[0]["contains_point"] is False


def test_find_counties_within_radius_groups_by_county():
    results = find_counties_within_radius(
        latitude=57.7089,
        longitude=11.9746,
        radius_km=30,
        geojson=VASTRA_GOTALAND_GEOJSON,
    )

    assert [result["lan_code"] for result in results] == ["14"]
    assert results[0]["county"] == "Västra Götalands län"


def test_find_counties_within_radius_includes_every_municipality_in_county():
    results = find_counties_within_radius(
        latitude=57.7089,
        longitude=11.9746,
        radius_km=5,
        geojson=VASTRA_GOTALAND_GEOJSON,
    )

    # Härryda's representative point is far outside the 5km radius, but
    # it belongs to the same county as Göteborg, which is within it, so
    # it should still be included in the county's region_codes.
    assert sorted(results[0]["region_codes"]) == ["1401", "1480"]


def test_find_counties_within_radius_uses_nearest_municipality_distance():
    results = find_counties_within_radius(
        latitude=57.7089,
        longitude=11.9746,
        radius_km=30,
        geojson=VASTRA_GOTALAND_GEOJSON,
    )

    assert results[0]["distance_km"] == pytest.approx(0)


def test_find_counties_within_radius_returns_empty_when_none_in_range():
    results = find_counties_within_radius(
        latitude=0,
        longitude=0,
        radius_km=1,
        geojson=VASTRA_GOTALAND_GEOJSON,
    )

    assert results == []


def test_point_in_geometry_true_when_inside_polygon():
    geometry = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]],
    }

    assert point_in_geometry(5, 5, geometry) is True


def test_point_in_geometry_false_when_outside_polygon():
    geometry = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]],
    }

    assert point_in_geometry(50, 50, geometry) is False


def test_point_in_geometry_respects_axis_order():
    # Rectangle spanning longitude 0-10, latitude 0-3.
    geometry = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [10, 0], [10, 3], [0, 3], [0, 0]]],
    }

    # latitude=1 (within 0-3), longitude=8 (within 0-10) -> inside
    assert point_in_geometry(1, 8, geometry) is True

    # latitude=8 (outside 0-3), longitude=1 (within 0-10) -> outside
    assert point_in_geometry(8, 1, geometry) is False


def test_point_in_geometry_respects_holes():
    geometry = {
        "type": "Polygon",
        "coordinates": [
            [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]],
            [[4, 4], [6, 4], [6, 6], [4, 6], [4, 4]],
        ],
    }

    assert point_in_geometry(5, 5, geometry) is False
    assert point_in_geometry(1, 1, geometry) is True


def test_point_in_geometry_true_inside_multipolygon_part():
    geometry = {
        "type": "MultiPolygon",
        "coordinates": [
            [[[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]],
            [[[10, 10], [12, 10], [12, 12], [10, 12], [10, 10]]],
        ],
    }

    assert point_in_geometry(1, 1, geometry) is True
    assert point_in_geometry(11, 11, geometry) is True
    assert point_in_geometry(50, 50, geometry) is False


def test_point_in_geometry_false_for_unsupported_geometry_type():
    geometry = {"type": "Point", "coordinates": [1, 1]}

    assert point_in_geometry(1, 1, geometry) is False
