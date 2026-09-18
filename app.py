"""Interactive geographic population explorer.

A Dash app: the user pans/zooms a map with a fixed-center selection pin
and a radius circle, sees which municipalities fall within that radius,
and views a population pyramid for them at a chosen year (with
play/pause to animate through the available years).
"""

import json
from pathlib import Path

import dash_leaflet as dl
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, dcc, html
from dash.exceptions import PreventUpdate

from scb_data.geography import (
    find_counties_within_radius,
    find_municipalities_within_radius,
)
from scb_data.queries import (
    get_available_months,
    get_max_pyramid_value,
    get_population_pyramid,
)
from scb_data.visualisation import create_population_pyramid

BASE_DIR = Path(__file__).resolve().parent

with open(
    BASE_DIR / "data" / "municipalities.geojson",
    encoding="utf-8",
) as file:
    MUNICIPALITIES_GEOJSON = json.load(file)


EMPTY_PYRAMID_DATA = pd.DataFrame(
    columns=["age_code", "age_group", "sex_code", "sex", "population"]
)

INITIAL_LAT = 57.7089
INITIAL_LON = 11.9746
INITIAL_CENTER = {"lat": INITIAL_LAT, "lng": INITIAL_LON}
INITIAL_RADIUS_KM = 10
MAX_RADIUS_KM = 100

# The month slider below is driven by an index into this list rather than the
# month strings themselves, since dcc.Slider needs numeric values. Fetched
# once at startup rather than hardcoded, so it reflects whatever months the
# pipeline has actually loaded.
AVAILABLE_MONTHS = get_available_months()
LATEST_MONTH_INDEX = len(AVAILABLE_MONTHS) - 1

PLAY_INTERVAL_MS = 800


app = Dash(__name__)


# Every panel below is sized with flex/minHeight-0 (not vh units on the map,
# as before) so the whole app fills exactly one viewport - map left, stats
# right - with no page scroll; only the municipality/county list scrolls
# internally if it grows long.
app.layout = html.Div(
    [
        html.Div(
            [
                html.H1(
                    "Population in Swedish Municipalities",
                    style={
                        "fontSize": "1.15rem",
                        "margin": 0,
                        "whiteSpace": "nowrap",
                    },
                ),

                html.Div(
                    [
                        html.Label("Level"),
                        dcc.RadioItems(
                            id="level-selector",
                            options=[
                                {
                                    "label": "Municipality",
                                    "value": "municipality",
                                },
                                {"label": "County", "value": "county"},
                            ],
                            value="municipality",
                            inline=True,
                        ),
                    ],
                    style={
                        "display": "flex",
                        "alignItems": "center",
                        "gap": "0.5rem",
                    },
                ),

                html.Div(
                    [
                        html.Label("Year"),
                        html.Div(
                            dcc.Slider(
                                id="month-slider",
                                min=0,
                                max=LATEST_MONTH_INDEX,
                                step=1,
                                value=LATEST_MONTH_INDEX,
                                # Marks show the year (all available months
                                # are December snapshots today); the full
                                # month string is in selection-output.
                                marks={
                                    i: month[:4]
                                    for i, month in enumerate(
                                        AVAILABLE_MONTHS
                                    )
                                },
                            ),
                            style={"width": "18rem"},
                        ),
                        html.Button("Play", id="play-button", n_clicks=0),
                        # Renders nothing; just fires on a timer while not
                        # disabled.
                        dcc.Interval(
                            id="play-interval",
                            interval=PLAY_INTERVAL_MS,
                            disabled=True,
                        ),
                    ],
                    style={
                        "display": "flex",
                        "alignItems": "center",
                        "gap": "0.75rem",
                        "flex": "1 1 auto",
                    },
                ),
            ],
            style={
                "display": "flex",
                "alignItems": "center",
                "gap": "2rem",
                "padding": "0.5rem 1rem",
                "borderBottom": "1px solid #ddd",
                "flex": "0 0 auto",
            },
        ),

        html.Div(
            [
                # Left: map + radius slider.
                html.Div(
                    [
                        html.Div(
                            [
                                dl.Map(
                                    [
                                        dl.TileLayer(),
                                        dl.Circle(
                                            id="radius-circle",
                                            center=INITIAL_CENTER,
                                            radius=INITIAL_RADIUS_KM * 1000,
                                        ),
                                    ],
                                    id="map",
                                    center=INITIAL_CENTER,
                                    zoom=5,
                                    # trackViewport (on by default) reports
                                    # the map's center/zoom/bounds back to
                                    # Dash on every pan/zoom, via this
                                    # component's own "center" prop.
                                    trackViewport=True,
                                    style={"height": "100%"},
                                ),

                                # The selection point is a fixed
                                # screen-center overlay, not a real Leaflet
                                # marker: it never moves on screen, the user
                                # pans/zooms the map underneath it, and its
                                # geographic position is simply the map's
                                # current center (see callback).
                                html.Div(
                                    "📍",
                                    style={
                                        "position": "absolute",
                                        "top": "50%",
                                        "left": "50%",
                                        "transform": (
                                            "translate(-50%, -100%)"
                                        ),
                                        "fontSize": "32px",
                                        "pointerEvents": "none",
                                        "zIndex": "1000",
                                    },
                                ),
                            ],
                            style={
                                "position": "relative",
                                "flex": "1 1 auto",
                                "minHeight": 0,
                            },
                        ),

                        html.Div(
                            [
                                html.Label("Radius (km)"),
                                dcc.Slider(
                                    id="radius-slider",
                                    min=1,
                                    max=MAX_RADIUS_KM,
                                    step=1,
                                    value=INITIAL_RADIUS_KM,
                                    marks={
                                        km: str(km)
                                        for km in range(
                                            0, MAX_RADIUS_KM + 1, 20
                                        )
                                    },
                                    tooltip={
                                        "placement": "bottom",
                                        "always_visible": True,
                                    },
                                ),
                            ],
                            style={
                                "padding": "0.5rem 1.5rem",
                                "flex": "0 0 auto",
                            },
                        ),
                    ],
                    style={
                        "flex": "1 1 60%",
                        "display": "flex",
                        "flexDirection": "column",
                        "minWidth": 0,
                        "minHeight": 0,
                    },
                ),

                # Right: selection summary, area list, population pyramid.
                html.Div(
                    [
                        html.Div(
                            "No selection yet",
                            id="selection-output",
                            style={"flex": "0 0 auto"},
                        ),

                        html.Div(
                            id="municipalities-output",
                            # A fixed height (rather than a percentage of
                            # the flex column) so it reliably scrolls
                            # internally instead of clipping when the list
                            # is long or the viewport is short.
                            style={
                                "flex": "0 0 10rem",
                                "overflowY": "auto",
                            },
                        ),

                        dcc.Graph(
                            id="population-pyramid",
                            style={"flex": "1 1 auto", "minHeight": 0},
                            config={"responsive": True},
                        ),
                    ],
                    style={
                        "flex": "1 1 40%",
                        "display": "flex",
                        "flexDirection": "column",
                        "minWidth": 0,
                        "minHeight": 0,
                        "padding": "0.5rem 1rem",
                        "overflow": "hidden",
                    },
                ),
            ],
            style={
                "display": "flex",
                "flex": "1 1 auto",
                "minHeight": 0,
                "overflow": "hidden",
            },
        ),
    ],
    style={
        "height": "100vh",
        "display": "flex",
        "flexDirection": "column",
        "overflow": "hidden",
        "fontFamily": "system-ui, -apple-system, 'Segoe UI', sans-serif",
    },
)


@app.callback(
    Output("selection-output", "children"),
    Input("map", "center"),
    Input("radius-slider", "value"),
    Input("month-slider", "value"),
)
def display_selection(
    center: dict | None,
    radius_km: int,
    month_index: int,
) -> str | html.Div:
    """Show the current selection point, radius, and year as plain text.

    Args:
        center: The map's current center, as {"lat": ..., "lng": ...},
            or None before the map has reported one.
        radius_km: The selected radius, in kilometers.
        month_index: Index into AVAILABLE_MONTHS for the selected year.

    Returns:
        A placeholder message if center is None, otherwise a div listing
        latitude, longitude, radius, and month.
    """
    if not center:
        return "No selection yet"

    lat = center.get("lat")
    lon = center.get("lng")

    return html.Div(
        [
            html.Div(f"Latitude: {lat}"),
            html.Div(f"Longitude: {lon}"),
            html.Div(f"Radius: {radius_km} km"),
            html.Div(f"Month: {AVAILABLE_MONTHS[month_index]}"),
        ]
    )


@app.callback(
    Output("play-interval", "disabled"),
    Output("play-button", "children"),
    Input("play-button", "n_clicks"),
    State("play-interval", "disabled"),
)
def toggle_play(n_clicks: int, is_disabled: bool) -> tuple[bool, str]:
    """Start/stop the year-slider animation when the play button is clicked.

    Args:
        n_clicks: Number of times the play button has been clicked. 0
            (its initial value) means this is the callback's unavoidable
            firing at page load, not a real click, and is ignored so
            playback doesn't start on its own.
        is_disabled: Whether play-interval is currently disabled (i.e.
            whether playback is currently paused).

    Returns:
        The new (disabled, button label) pair, toggled from the current
        state: enabling the interval and switching the label to "Pause"
        if playback was paused, or the reverse if it was playing.
    """
    if not n_clicks:
        raise PreventUpdate

    playing = is_disabled

    return not playing, ("Pause" if playing else "Play")


@app.callback(
    Output("month-slider", "value"),
    Input("play-interval", "n_intervals"),
    State("month-slider", "value"),
    prevent_initial_call=True,
)
def advance_month(n_intervals: int, month_index: int) -> int:
    """Advance the year slider by one step on each play-interval tick.

    Args:
        n_intervals: Number of interval ticks so far (unused; only its
            firing matters, not its value).
        month_index: The year slider's current index into
            AVAILABLE_MONTHS.

    Returns:
        The next index, wrapping back to 0 after the last available
        month so the animation loops instead of stopping at the end.
    """
    return (month_index + 1) % len(AVAILABLE_MONTHS)


@app.callback(
    Output("radius-circle", "center"),
    Output("radius-circle", "radius"),
    Input("map", "center"),
    Input("radius-slider", "value"),
)
def update_radius_circle(
    center: dict | None,
    radius_km: int,
) -> tuple[dict, int]:
    """Keep the radius circle centered on the map with the selected radius.

    Args:
        center: The map's current center, as {"lat": ..., "lng": ...},
            or None before the map has reported one.
        radius_km: The selected radius, in kilometers.

    Returns:
        The circle's new (center, radius_in_meters), falling back to
        INITIAL_CENTER if center is None.
    """
    if not center:
        center = INITIAL_CENTER

    return center, radius_km * 1000


@app.callback(
    Output("municipalities-output", "children"),
    Input("map", "center"),
    Input("radius-slider", "value"),
    Input("level-selector", "value"),
)
def display_municipalities(
    center: dict | None,
    radius_km: int,
    level: str,
) -> html.Div | None:
    """List the municipalities or counties within the selected radius.

    Args:
        center: The map's current center, as {"lat": ..., "lng": ...},
            or None before the map has reported one.
        radius_km: The selected radius, in kilometers.
        level: "municipality" or "county" (the level-selector's value).

    Returns:
        None if center is None, a "none within radius" message if the
        radius contains none at the chosen level, or a div with a count
        and a bullet list (nearest first, distance in km, flagging any
        area whose actual boundary contains the selected point).
    """
    if not center:
        return None

    if level == "county":
        areas = find_counties_within_radius(
            latitude=center["lat"],
            longitude=center["lng"],
            radius_km=radius_km,
            geojson=MUNICIPALITIES_GEOJSON,
        )
        noun = "counties"
        name_key = "county"
    else:
        areas = find_municipalities_within_radius(
            latitude=center["lat"],
            longitude=center["lng"],
            radius_km=radius_km,
            geojson=MUNICIPALITIES_GEOJSON,
        )
        noun = "municipalities"
        name_key = "region"

    if not areas:
        return html.Div(f"No {noun} within radius")

    return html.Div(
        [
            html.Div(f"{len(areas)} {noun} within radius:"),
            html.Ul(
                [
                    html.Li(
                        f"{area[name_key]} ({area['distance_km']:.1f} km)"
                        + (
                            " — contains selected point"
                            if area["contains_point"]
                            else ""
                        )
                    )
                    for area in areas
                ]
            ),
        ]
    )


@app.callback(
    Output("population-pyramid", "figure"),
    Input("map", "center"),
    Input("radius-slider", "value"),
    Input("month-slider", "value"),
    Input("level-selector", "value"),
)
def update_population_pyramid(
    center: dict | None,
    radius_km: int,
    month_index: int,
    level: str,
) -> go.Figure:
    """Build the population pyramid for the selected area and year.

    Args:
        center: The map's current center, as {"lat": ..., "lng": ...},
            or None before the map has reported one.
        radius_km: The selected radius, in kilometers.
        month_index: Index into AVAILABLE_MONTHS for the selected year.
        level: "municipality" or "county" (the level-selector's value).
            At "county", the pyramid covers every municipality in each
            matched county, not just the ones inside the radius.

    Returns:
        An empty pyramid if center is None or no areas fall within the
        radius at the chosen level, otherwise the population pyramid
        summed across those areas for the selected year, with the
        x-axis fixed to the largest value seen across every year of
        the current selection so the axis doesn't rescale as the year
        slider or play/pause moves through months.
    """
    if not center:
        return create_population_pyramid(EMPTY_PYRAMID_DATA)

    if level == "county":
        counties = find_counties_within_radius(
            latitude=center["lat"],
            longitude=center["lng"],
            radius_km=radius_km,
            geojson=MUNICIPALITIES_GEOJSON,
        )
        region_codes = [
            code for county in counties for code in county["region_codes"]
        ]
    else:
        municipalities = find_municipalities_within_radius(
            latitude=center["lat"],
            longitude=center["lng"],
            radius_km=radius_km,
            geojson=MUNICIPALITIES_GEOJSON,
        )
        region_codes = [m["region_code"] for m in municipalities]

    if not region_codes:
        return create_population_pyramid(EMPTY_PYRAMID_DATA)

    month = AVAILABLE_MONTHS[month_index]
    pyramid_data = get_population_pyramid(region_codes, month)
    axis_max = get_max_pyramid_value(region_codes)

    return create_population_pyramid(pyramid_data, axis_max=axis_max)


if __name__ == "__main__":
    app.run(debug=True)
