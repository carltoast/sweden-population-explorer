"""Tests for scb_data.visualisation."""

import pandas as pd
import plotly.graph_objects as go

from scb_data.visualisation import (
    add_municipality_boundaries,
    create_population_map,
    create_population_pyramid,
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

    original_geometry = geojson["features"][0]["geometry"]
    original_ring = original_geometry["coordinates"][0].copy()

    prepare_geojson(geojson)

    assert original_geometry["coordinates"][0] == original_ring


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
            "region_code": ["1480", "0180"],
            "region": ["Göteborg", "Stockholm"],
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
            "region_code": ["1480"],
            "region": ["Göteborg"],
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
            "region_code": ["1480"],
            "region": ["Göteborg"],
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
            "region_code": ["1480"],
            "region": ["Göteborg"],
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


def _population_pyramid_fixture():
    return pd.DataFrame(
        {
            "age_code": ["-9", "-9", "10-19", "10-19"],
            "age_group": [
                "0–9 years", "0–9 years", "10–19 years", "10–19 years",
            ],
            "sex_code": ["1", "2", "1", "2"],
            "sex": ["men", "women", "men", "women"],
            "population": [100, 90, 200, 210],
        }
    )


def test_create_population_pyramid_returns_figure():
    fig = create_population_pyramid(_population_pyramid_fixture())

    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 2
    assert all(isinstance(trace, go.Bar) for trace in fig.data)


def test_create_population_pyramid_male_bars_extend_left():
    fig = create_population_pyramid(_population_pyramid_fixture())

    male_trace = next(trace for trace in fig.data if trace.name == "Male")

    assert list(male_trace.x) == [-100, -200]


def test_create_population_pyramid_female_bars_extend_right():
    fig = create_population_pyramid(_population_pyramid_fixture())

    female_trace = next(trace for trace in fig.data if trace.name == "Female")

    assert list(female_trace.x) == [90, 210]


def test_create_population_pyramid_tick_labels_have_no_negative_sign():
    fig = create_population_pyramid(_population_pyramid_fixture())

    assert all("-" not in label for label in fig.layout.xaxis.ticktext)


def test_create_population_pyramid_tick_values_are_symmetric():
    fig = create_population_pyramid(_population_pyramid_fixture())

    tick_values = list(fig.layout.xaxis.tickvals)

    assert tick_values == sorted(tick_values)
    assert tick_values[0] == -tick_values[-1]
    assert 0 in tick_values


def test_create_population_pyramid_range_matches_outer_ticks():
    fig = create_population_pyramid(_population_pyramid_fixture())

    tick_values = list(fig.layout.xaxis.tickvals)

    assert list(fig.layout.xaxis.range) == [tick_values[0], tick_values[-1]]


def test_create_population_pyramid_axis_max_fixes_range_across_frames():
    small_frame = create_population_pyramid(
        _population_pyramid_fixture(), axis_max=100_000
    )
    large_frame = create_population_pyramid(
        pd.DataFrame(
            {
                "age_code": ["-9"],
                "age_group": ["0–9 years"],
                "sex_code": ["1"],
                "sex": ["men"],
                "population": [99_000],
            }
        ),
        axis_max=100_000,
    )

    assert (
        list(small_frame.layout.xaxis.range)
        == list(large_frame.layout.xaxis.range)
    )


def test_create_population_pyramid_axis_max_widens_ticks():
    default_fig = create_population_pyramid(_population_pyramid_fixture())
    widened_fig = create_population_pyramid(
        _population_pyramid_fixture(), axis_max=100_000
    )

    default_max = max(default_fig.layout.xaxis.tickvals)
    widened_max = max(widened_fig.layout.xaxis.tickvals)

    assert widened_max > default_max


def test_create_population_pyramid_axis_max_ignored_if_smaller():
    default_fig = create_population_pyramid(_population_pyramid_fixture())
    narrower_fig = create_population_pyramid(
        _population_pyramid_fixture(), axis_max=1
    )

    default_max = max(default_fig.layout.xaxis.tickvals)
    narrower_max = max(narrower_fig.layout.xaxis.tickvals)

    assert narrower_max == default_max


def test_create_population_pyramid_handles_missing_sex():
    data = pd.DataFrame(
        {
            "age_code": ["-9"],
            "age_group": ["0–9 years"],
            "sex_code": ["1"],
            "sex": ["men"],
            "population": [100],
        }
    )

    fig = create_population_pyramid(data)

    female_trace = next(trace for trace in fig.data if trace.name == "Female")

    assert list(female_trace.x) == [0]
