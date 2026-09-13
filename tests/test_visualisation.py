import pandas as pd
import plotly.graph_objects as go

from scb_data.visualisation import (
    add_municipality_boundaries,
    create_population_map,
    prepare_geojson,
)


def test_prepare_geojson_polygon_reverses_exterior_ring():
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"id": "1480"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [1, 1],
                            [2, 1],
                            [2, 2],
                            [1, 2],
                            [1, 1],
                        ]
                    ],
                },
            }
        ],
    }

    result = prepare_geojson(geojson)

    original_ring = geojson["features"][0]["geometry"]["coordinates"][0]
    result_ring = result["features"][0]["geometry"]["coordinates"][0]

    assert result_ring == original_ring[::-1]


def test_prepare_geojson_multipolygon_reverses_exterior_rings():
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"id": "1480"},
                "geometry": {
                    "type": "MultiPolygon",
                    "coordinates": [
                        [
                            [
                                [1, 1],
                                [2, 1],
                                [2, 2],
                                [1, 2],
                                [1, 1],
                            ]
                        ],
                        [
                            [
                                [3, 3],
                                [4, 3],
                                [4, 4],
                                [3, 4],
                                [3, 3],
                            ]
                        ],
                    ],
                },
            }
        ],
    }

    result = prepare_geojson(geojson)

    original_polygons = geojson["features"][0]["geometry"]["coordinates"]
    result_polygons = result["features"][0]["geometry"]["coordinates"]

    for original, result_polygon in zip(original_polygons, result_polygons):
        assert result_polygon[0] == original[0][::-1]


def test_prepare_geojson_does_not_modify_original():
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"id": "1480"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [1, 1],
                            [2, 1],
                            [2, 2],
                            [1, 2],
                            [1, 1],
                        ]
                    ],
                },
            }
        ],
    }

    original_ring = geojson["features"][0]["geometry"]["coordinates"][0].copy()

    prepare_geojson(geojson)

    assert geojson["features"][0]["geometry"]["coordinates"][0] == original_ring


def test_prepare_geojson_preserves_feature_properties():
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "id": "1480",
                    "kom_namn": "Göteborg",
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [1, 1],
                            [2, 1],
                            [2, 2],
                            [1, 2],
                            [1, 1],
                        ]
                    ],
                },
            }
        ],
    }

    result = prepare_geojson(geojson)

    assert result["features"][0]["properties"] == {
        "id": "1480",
        "kom_namn": "Göteborg",
    }


def test_add_municipality_boundaries_adds_one_trace_per_polygon():
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"id": "1"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [1, 1],
                            [2, 1],
                            [2, 2],
                            [1, 2],
                            [1, 1],
                        ]
                    ],
                },
            },
            {
                "type": "Feature",
                "properties": {"id": "2"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [3, 3],
                            [4, 3],
                            [4, 4],
                            [3, 4],
                            [3, 3],
                        ]
                    ],
                },
            },
        ],
    }

    fig = go.Figure()

    add_municipality_boundaries(fig, geojson)

    assert len(fig.data) == 2
    assert all(isinstance(trace, go.Scattergeo) for trace in fig.data)


def test_add_municipality_boundaries_handles_multipolygon():
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"id": "1"},
                "geometry": {
                    "type": "MultiPolygon",
                    "coordinates": [
                        [
                            [
                                [1, 1],
                                [2, 1],
                                [2, 2],
                                [1, 2],
                                [1, 1],
                            ]
                        ],
                        [
                            [
                                [3, 3],
                                [4, 3],
                                [4, 4],
                                [3, 4],
                                [3, 3],
                            ]
                        ],
                    ],
                },
            }
        ],
    }

    fig = go.Figure()

    add_municipality_boundaries(fig, geojson)

    assert len(fig.data) == 2
    assert all(isinstance(trace, go.Scattergeo) for trace in fig.data)


def test_add_municipality_boundaries_skips_unsupported_geometry():
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"id": "1"},
                "geometry": {
                    "type": "Point",
                    "coordinates": [1, 1],
                },
            }
        ],
    }

    fig = go.Figure()

    add_municipality_boundaries(fig, geojson)

    assert len(fig.data) == 0


def test_create_population_map_returns_figure():
    data = pd.DataFrame(
        {
            "municipality_code": ["1480", "0180"],
            "municipality_name": ["Göteborg", "Stockholm"],
            "population": [608993, 995574],
        }
    )

    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"id": "1480"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [1, 1],
                            [2, 1],
                            [2, 2],
                            [1, 2],
                            [1, 1],
                        ]
                    ],
                },
            },
            {
                "type": "Feature",
                "properties": {"id": "0180"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [3, 3],
                            [4, 3],
                            [4, 4],
                            [3, 4],
                            [3, 3],
                        ]
                    ],
                },
            },
        ],
    }

    fig = create_population_map(data, geojson)

    assert isinstance(fig, go.Figure)


def test_create_population_map_contains_choropleth_and_boundaries():
    data = pd.DataFrame(
        {
            "municipality_code": ["1480"],
            "municipality_name": ["Göteborg"],
            "population": [608993],
        }
    )

    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"id": "1480"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [1, 1],
                            [2, 1],
                            [2, 2],
                            [1, 2],
                            [1, 1],
                        ]
                    ],
                },
            }
        ],
    }

    fig = create_population_map(data, geojson)

    assert len(fig.data) == 2
    assert isinstance(fig.data[0], go.Choropleth)
    assert isinstance(fig.data[1], go.Scattergeo)


def test_create_population_map_uses_population_data():
    data = pd.DataFrame(
        {
            "municipality_code": ["1480"],
            "municipality_name": ["Göteborg"],
            "population": [608993],
        }
    )

    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"id": "1480"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [1, 1],
                            [2, 1],
                            [2, 2],
                            [1, 2],
                            [1, 1],
                        ]
                    ],
                },
            }
        ],
    }

    fig = create_population_map(data, geojson)

    choropleth = fig.data[0]

    assert list(choropleth.locations) == ["1480"]
    assert list(choropleth.z) == [608993]


def test_create_population_map_uses_municipality_code_as_feature_id():
    data = pd.DataFrame(
        {
            "municipality_code": ["1480"],
            "municipality_name": ["Göteborg"],
            "population": [608993],
        }
    )

    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"id": "1480"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [1, 1],
                            [2, 1],
                            [2, 2],
                            [1, 2],
                            [1, 1],
                        ]
                    ],
                },
            }
        ],
    }

    fig = create_population_map(data, geojson)

    choropleth = fig.data[0]

    assert choropleth.featureidkey == "properties.id"