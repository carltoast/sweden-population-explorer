"""Plotly figures: municipality choropleth map and population pyramid."""

import math

import pandas as pd
import plotly.graph_objects as go

# Aqua/violet (categorical slots 3 and 7): a gender-neutral pair, re-checked
# against the dataviz skill's validator for this specific (non-adjacent)
# pairing since the palette only pre-validates adjacent slots - CVD Delta E
# 31.1, normal-vision Delta E 35.8 (target/floor 8.0/15.0), both well clear.
# Aqua's contrast against white is 2.74 (just under the 3:1 floor); the
# palette's documented mitigation for that - visible direct labels - is
# already satisfied by this chart's legend and hover labels.
MALE_COLOR = "#1baf7a"
FEMALE_COLOR = "#4a3aa7"


def prepare_geojson(geojson: dict) -> dict:
    """Prepare municipality GeoJSON for Plotly rendering.

    Plotly's Choropleth/Scattergeo render Polygon/MultiPolygon exterior
    rings incorrectly unless their winding order is reversed first.

    Args:
        geojson: A GeoJSON FeatureCollection of municipalities, with
            Polygon or MultiPolygon geometries.

    Returns:
        An equivalent FeatureCollection (the input is not modified) with
        every exterior ring's coordinate order reversed.
    """
    features = []

    for feature in geojson["features"]:
        feature = feature.copy()
        geometry = feature["geometry"].copy()

        if geometry["type"] == "Polygon":
            coordinates = geometry["coordinates"].copy()
            coordinates[0] = coordinates[0][::-1]
            geometry["coordinates"] = coordinates

        elif geometry["type"] == "MultiPolygon":
            coordinates = []

            for polygon in geometry["coordinates"]:
                polygon = polygon.copy()
                polygon[0] = polygon[0][::-1]
                coordinates.append(polygon)

            geometry["coordinates"] = coordinates

        feature["geometry"] = geometry
        features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features,
    }


def add_municipality_boundaries(fig: go.Figure, geojson: dict) -> None:
    """Add municipality boundary lines to a Plotly geographic figure.

    Adds one Scattergeo line trace per polygon (municipalities with a
    MultiPolygon geometry get one trace per part). Modifies fig in
    place; features whose geometry is neither Polygon nor MultiPolygon
    are skipped.

    Args:
        fig: Plotly figure with a geographic (geo) subplot to draw on.
        geojson: A GeoJSON FeatureCollection of municipalities.
    """
    for feature in geojson["features"]:
        geometry = feature["geometry"]

        if geometry["type"] == "Polygon":
            polygons = [geometry["coordinates"]]
        elif geometry["type"] == "MultiPolygon":
            polygons = geometry["coordinates"]
        else:
            continue

        for polygon in polygons:
            ring = polygon[0]

            fig.add_trace(
                go.Scattergeo(
                    lon=[point[0] for point in ring],
                    lat=[point[1] for point in ring],
                    mode="lines",
                    line={"color": "black", "width": 0.5},
                    hoverinfo="skip",
                    showlegend=False,
                )
            )


def create_population_map(data: pd.DataFrame, geojson: dict) -> go.Figure:
    """Create a choropleth map of municipal population.

    Args:
        data: Columns region_code and population, one row per
            municipality (e.g. from scb_data.queries.get_population_by_
            region).
        geojson: A GeoJSON FeatureCollection of municipalities, matched
            to data via region_code / properties.id.

    Returns:
        A figure with a Choropleth trace (population by municipality)
        plus municipality boundary lines.
    """
    data = data.copy()
    data["region_code"] = data["region_code"].astype(str)

    plotly_geojson = prepare_geojson(geojson)

    fig = go.Figure(
        go.Choropleth(
            geojson=plotly_geojson,
            locations=data["region_code"],
            z=data["population"],
            featureidkey="properties.id",
            colorscale="YlOrRd",
            marker_line_width=0,
            colorbar_title="Population",
            hovertemplate=(
                "<b>%{customdata}</b>"
                "<br>Population: %{z:,.0f}"
                "<extra></extra>"
            ),
            customdata=data["region"],
        )
    )

    add_municipality_boundaries(fig, plotly_geojson)

    fig.update_geos(
        fitbounds="geojson",
        visible=False,
    )

    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        paper_bgcolor="white",
    )

    return fig


def _nice_number(value: float) -> float:
    """Round up to a visually clean number (1/2/5 x a power of ten).

    Args:
        value: Value to round; e.g. 42 -> 50, 3 -> 5, 120 -> 200.

    Returns:
        The rounded value, or 0 if value is not positive.
    """
    if value <= 0:
        return 0

    exponent = math.floor(math.log10(value))
    fraction = value / (10**exponent)

    if fraction <= 1:
        nice_fraction = 1
    elif fraction <= 2:
        nice_fraction = 2
    elif fraction <= 5:
        nice_fraction = 5
    else:
        nice_fraction = 10

    return nice_fraction * (10**exponent)


def _symmetric_ticks(max_value: float) -> tuple[list[float], list[str]]:
    """Build tick values/labels for a diverging axis, absolute-valued.

    Five ticks (-max, -max/2, 0, max/2, max) are used so a bar chart
    with negated values on one side (e.g. a population pyramid) can
    still show clean, comma-formatted, always-positive labels - Plotly
    has no built-in way to format a tick's absolute value.

    Args:
        max_value: The largest magnitude to be plotted on this axis.

    Returns:
        A (tick_values, tick_text) pair: five symmetric tick positions,
        and their matching absolute-value, comma-formatted labels.
    """
    nice_max = _nice_number(max_value) if max_value > 0 else 1
    half = nice_max / 2

    tick_values = [-nice_max, -half, 0, half, nice_max]
    tick_text = [f"{abs(value):,.0f}" for value in tick_values]

    return tick_values, tick_text


def create_population_pyramid(
    data: pd.DataFrame,
    axis_max: float | None = None,
) -> go.Figure:
    """Create a population pyramid: male population left, female right.

    Args:
        data: Rows with age_code, age_group, sex_code ("1" male, "2"
            female), and population, already ordered by age (e.g. from
            scb_data.queries.get_population_pyramid). May be empty.
        axis_max: If given, the axis is scaled to at least this
            magnitude even if data's own max is smaller - used to hold
            a fixed x-axis range across an entire play/pause animation
            (e.g. the max over every year of the selected area) rather
            than rescaling to each frame's own max. Defaults to None,
            which scales to data's own max as before.

    Returns:
        A figure with two horizontal bar traces (male, female) sharing
        one y-axis of age groups, male population negated so its bars
        extend left and female bars extend right from a shared zero.
    """
    pivot = data.pivot_table(
        index=["age_code", "age_group"],
        columns="sex_code",
        values="population",
        fill_value=0,
        sort=False,
        observed=True,
    ).reset_index()

    age_labels = pivot["age_group"]
    empty_column = pd.Series(0, index=pivot.index)
    male_population = pivot["1"] if "1" in pivot else empty_column
    female_population = pivot["2"] if "2" in pivot else empty_column

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            y=age_labels,
            x=-male_population,
            customdata=male_population,
            name="Male",
            orientation="h",
            marker_color=MALE_COLOR,
            hovertemplate="%{y}<br>Male: %{customdata:,.0f}<extra></extra>",
        )
    )

    fig.add_trace(
        go.Bar(
            y=age_labels,
            x=female_population,
            customdata=female_population,
            name="Female",
            orientation="h",
            marker_color=FEMALE_COLOR,
            hovertemplate="%{y}<br>Female: %{customdata:,.0f}<extra></extra>",
        )
    )

    max_population = max(male_population.max(), female_population.max())
    if axis_max is not None:
        max_population = max(max_population, axis_max)
    tick_values, tick_text = _symmetric_ticks(max_population)

    fig.update_layout(
        barmode="overlay",
        xaxis={
            "title": "Population",
            "range": [tick_values[0], tick_values[-1]],
            "tickvals": tick_values,
            "ticktext": tick_text,
            "gridcolor": "#e1e0d9",
            "zerolinecolor": "#c3c2b7",
        },
        yaxis={"title": "Age group"},
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02},
    )

    return fig
