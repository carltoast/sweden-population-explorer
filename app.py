"""Interactive geographic population explorer.

A Dash app: the user pans/zooms a borders-only map of Sweden with a
fixed screen-center marker and radius ring, sees which municipalities
or counties fall within that radius (highlighted on the map and named
in the population pyramid's title), and views the pyramid at a chosen
year, with play/pause to animate through the available years.

The marker and radius ring are plain CSS overlays fixed to the screen
center, not geographic Leaflet layers - a Leaflet layer's position
only updates back to Dash on "moveend" (see update_boundary_highlights),
which made an earlier Leaflet-circle implementation visibly lag behind
the cursor until a drag was released. A screen-fixed overlay has no
such lag: its position is always the screen center by construction,
and only its pixel size (for the ring) needs recomputing from the
selected radius and the map's current zoom/latitude.
"""

import json
import math
from pathlib import Path

import dash_leaflet as dl
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, dcc, html
from dash.exceptions import PreventUpdate

from scb_data.geography import (
    dissolve_municipalities_to_counties,
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

# Computed once at startup, not per-request: dissolving ~290 municipality
# polygons into 21 county polygons is pure CPU work independent of any
# request, so it's done here rather than in a callback.
COUNTIES_GEOJSON = dissolve_municipalities_to_counties(MUNICIPALITIES_GEOJSON)

BOUNDARY_STYLE = {
    "color": "#52514e",
    "weight": 1,
    "fillColor": "#cde2fb",
    "fillOpacity": 0.5,
}

# Areas within the radius (but not the one the pin is actually in) get a
# more saturated fill than BOUNDARY_STYLE; the one area the pin is actually
# inside of gets a bolder, distinctly-colored outline on top of that -
# these are separate dl.GeoJSON layers (see update_boundary_highlights)
# rather than a per-feature style function, since that needs a clientside
# JS callback (dash-leaflet's style/hideout props take a function for
# per-feature styling, which dash-extensions provides but this project
# doesn't otherwise depend on) - stacking a few static-styled layers with
# different data subsets gets the same visual result with no JS.
IN_RADIUS_STYLE = {
    "color": "#2a5c8a",
    "weight": 1.5,
    "fillColor": "#7fb2e0",
    "fillOpacity": 0.65,
}
SELECTED_AREA_STYLE = {
    "color": "#8a5a00",
    "weight": 2.5,
    "fillColor": "#f2a900",
    "fillOpacity": 0.55,
}
EMPTY_GEOJSON = {"type": "FeatureCollection", "features": []}

# Sweden's real bounding box (from municipalities.geojson) is only ~13.2°
# of longitude wide but ~13.7° of latitude tall - a narrow, elongated shape.
# The zoom level that fits its full height into the map area (so the whole
# country is visible by default, as intended) shows a viewport far WIDER
# than that, because the map area itself is a wide/landscape panel. Leaflet's
# maxBounds restricts the *viewport*, not just the pin - if the bounds box
# were only lightly padded (as Sweden's own edges are), that already-wide
# viewport would have almost nowhere to slide sideways before its own edge
# hit the bounds wall, making panning feel frozen/snappy until zoomed in far
# enough to shrink the viewport below the bounds size. Padding generously
# (especially east-west, well beyond the country's own width) gives the
# viewport real room to move at the default zoom too.
SWEDEN_BOUNDS = [[47.3, -14.0], [77.1, 49.2]]
MIN_ZOOM = 4
INITIAL_ZOOM = 5

EMPTY_PYRAMID_DATA = pd.DataFrame(
    columns=["age_code", "age_group", "sex_code", "sex", "population"]
)

INITIAL_LAT = 57.7089
INITIAL_LON = 11.9746
INITIAL_CENTER = {"lat": INITIAL_LAT, "lng": INITIAL_LON}
INITIAL_RADIUS_KM = 10

# Sweden's own corner-to-corner distance is roughly 1,700 km, so 2000 km
# comfortably covers the whole country from any starting point - dragging
# the radius slider all the way up gives country-wide aggregate stats.
MIN_RADIUS_KM = 1
MAX_RADIUS_KM = 2000


def radius_slider_value_to_km(slider_value: float) -> int:
    """Convert the radius slider's raw (log-scale) value into kilometers.

    The slider's own value is log10(radius_km), not radius_km itself,
    so a small drag near the low end still gives fine control (1-10
    km) while reaching up to MAX_RADIUS_KM at the top - a linear
    slider over the same 1-2000 km range would make anything under
    ~100 km nearly impossible to select precisely.

    Args:
        slider_value: The radius-slider's raw value (an exponent).

    Returns:
        The corresponding radius in kilometers, rounded to the
        nearest whole km.
    """
    return round(10**slider_value)


def radius_km_to_slider_value(radius_km: float) -> float:
    """Convert a radius in kilometers into the slider's raw log value.

    Args:
        radius_km: A radius in kilometers.

    Returns:
        log10(radius_km): the slider's own value representation.
    """
    return math.log10(radius_km)


def _meters_per_pixel(latitude: float, zoom: int) -> float:
    """Compute Web Mercator ground resolution at a latitude and zoom.

    Args:
        latitude: Latitude, in degrees (ground resolution per pixel
            narrows toward the poles at a given zoom, hence the
            cosine term).
        zoom: The map's current Leaflet zoom level.

    Returns:
        Meters of ground distance represented by one screen pixel.
    """
    return 156543.03392 * math.cos(math.radians(latitude)) / (2**zoom)


def radius_km_to_px(radius_km: float, latitude: float, zoom: int) -> float:
    """Convert a ground radius into an on-screen pixel radius.

    Used to size the fixed-screen radius ring (see module docstring)
    so it still represents the true ground distance at the map's
    current position and zoom, despite not being a geographic layer.

    Args:
        radius_km: The selected radius, in kilometers.
        latitude: The map center's latitude, in degrees.
        zoom: The map's current Leaflet zoom level.

    Returns:
        The radius in screen pixels.
    """
    return (radius_km * 1000) / _meters_per_pixel(latitude, zoom)


def _summarize_areas(areas: list[dict], name_key: str) -> str:
    """Build a compact area-summary string for the pyramid's title.

    Args:
        areas: Area dicts sorted nearest-first (as returned by
            find_municipalities_within_radius or
            find_counties_within_radius), each with a name_key.
        name_key: "region" for municipalities, "county" for counties.

    Returns:
        The nearest three area names, comma-separated, with a "+N
        more" suffix if there are more than three, or "No areas
        selected" if areas is empty.
    """
    if not areas:
        return "No areas selected"

    names = [area[name_key] for area in areas]
    shown = names[:3]
    summary = ", ".join(shown)
    remaining = len(names) - len(shown)

    if remaining > 0:
        summary += f" +{remaining} more"

    return summary


CENTER_MARKER_STYLE = {
    "position": "absolute",
    "top": "50%",
    "left": "50%",
    "transform": "translate(-50%, -50%)",
    "width": "10px",
    "height": "10px",
    "borderRadius": "50%",
    "backgroundColor": "#2b2b2b",
    "border": "2px solid white",
    "boxShadow": "0 0 2px rgba(0, 0, 0, 0.6)",
    "pointerEvents": "none",
    "zIndex": 1001,
}

RADIUS_RING_BASE_STYLE = {
    "position": "absolute",
    "top": "50%",
    "left": "50%",
    "transform": "translate(-50%, -50%)",
    "borderRadius": "50%",
    "border": "2px solid #52514e",
    "backgroundColor": "rgba(82, 81, 78, 0.08)",
    "pointerEvents": "none",
    "zIndex": 900,
}

INITIAL_RADIUS_PX = radius_km_to_px(
    INITIAL_RADIUS_KM, INITIAL_LAT, INITIAL_ZOOM
)

MAP_OVERLAY_STYLE = {
    "position": "absolute",
    "zIndex": 1000,
    "background": "rgba(255, 255, 255, 0.9)",
    "padding": "0.4rem 0.9rem",
    "borderRadius": "8px",
    "boxShadow": "0 1px 4px rgba(0, 0, 0, 0.25)",
}

RADIUS_SLIDER_MAX = math.log10(MAX_RADIUS_KM)

# The month slider below is driven by an index into this list rather than the
# month strings themselves, since dcc.Slider needs numeric values. Fetched
# once at startup rather than hardcoded, so it reflects whatever months the
# pipeline has actually loaded.
AVAILABLE_MONTHS = get_available_months()
LATEST_MONTH_INDEX = len(AVAILABLE_MONTHS) - 1

PLAY_INTERVAL_MS = 800


app = Dash(__name__)


# No page-level title bar: once the level/radius controls float over the
# map and the year controls sit above the pyramid, nothing was left in it.
# The whole app is one flex row filling exactly one viewport - map left,
# stats right - with no page scroll.
app.layout = html.Div(
    [
        # Left: map, with the level selector, radius slider, marker, and
        # radius ring all floating on top of it rather than taking their
        # own layout space.
        html.Div(
            [
                dl.Map(
                    [
                        # No tile basemap: the map is just
                        # municipality/county borders on a plain
                        # background (see BOUNDARY_STYLE and
                        # assets/layout.css's .leaflet-container rule
                        # for the "sea" fill), swapped between the two
                        # levels by update_boundaries_layer below.
                        dl.GeoJSON(
                            id="boundaries-layer",
                            data=MUNICIPALITIES_GEOJSON,
                            style=BOUNDARY_STYLE,
                        ),
                        # Stacked on top of boundaries-layer; see
                        # update_boundary_highlights.
                        dl.GeoJSON(
                            id="in-radius-layer",
                            data=EMPTY_GEOJSON,
                            style=IN_RADIUS_STYLE,
                        ),
                        dl.GeoJSON(
                            id="selected-area-layer",
                            data=EMPTY_GEOJSON,
                            style=SELECTED_AREA_STYLE,
                        ),
                    ],
                    id="map",
                    center=INITIAL_CENTER,
                    zoom=INITIAL_ZOOM,
                    minZoom=MIN_ZOOM,
                    maxBounds=SWEDEN_BOUNDS,
                    maxBoundsViscosity=1.0,
                    # trackViewport (on by default) reports the map's
                    # center/zoom/bounds back to Dash on every pan/zoom,
                    # via this component's own "center"/"zoom" props.
                    trackViewport=True,
                    style={"height": "100%"},
                ),

                # Fixed screen-center marker and radius ring - see the
                # module docstring for why these are plain CSS overlays
                # rather than Leaflet layers.
                html.Div(style=CENTER_MARKER_STYLE),
                html.Div(
                    id="radius-ring",
                    style={
                        **RADIUS_RING_BASE_STYLE,
                        "width": f"{INITIAL_RADIUS_PX}px",
                        "height": f"{INITIAL_RADIUS_PX}px",
                    },
                ),

                # Level selector, floating top-center on the map.
                html.Div(
                    dcc.RadioItems(
                        id="level-selector",
                        options=[
                            {"label": "County", "value": "county"},
                            {
                                "label": "Municipality",
                                "value": "municipality",
                            },
                        ],
                        value="county",
                        inline=True,
                    ),
                    style={
                        **MAP_OVERLAY_STYLE,
                        "top": "0.75rem",
                        "left": "50%",
                        "transform": "translateX(-50%)",
                    },
                ),

                # Radius slider, floating bottom-center on the map. A
                # log-scale slider (see radius_slider_value_to_km) so it
                # keeps fine control at small radii while still reaching
                # MAX_RADIUS_KM; its own tooltip would show the raw
                # exponent value, not km, so update_radius_label drives a
                # plain text readout instead.
                html.Div(
                    [
                        html.Div(
                            id="radius-label",
                            style={
                                "textAlign": "center",
                                "fontSize": "0.85rem",
                                "fontWeight": 600,
                                "marginBottom": "0.3rem",
                            },
                        ),
                        dcc.Slider(
                            id="radius-slider",
                            min=0,
                            max=RADIUS_SLIDER_MAX,
                            step=0.01,
                            value=radius_km_to_slider_value(
                                INITIAL_RADIUS_KM
                            ),
                            marks={
                                exponent: str(10**exponent)
                                for exponent in range(
                                    0, math.ceil(RADIUS_SLIDER_MAX) + 1
                                )
                            },
                            updatemode="drag",
                            allow_direct_input=False,
                        ),
                    ],
                    style={
                        **MAP_OVERLAY_STYLE,
                        "bottom": "0.75rem",
                        "left": "50%",
                        "transform": "translateX(-50%)",
                        "width": "18rem",
                        "maxWidth": "90%",
                    },
                ),
            ],
            style={
                "position": "relative",
                "flex": "1 1 60%",
                "minWidth": 0,
            },
        ),

        # Right: population pyramid above the year controls.
        html.Div(
            [
                dcc.Graph(
                    id="population-pyramid",
                    style={"flex": "1 1 auto", "minHeight": 0},
                    config={"responsive": True},
                ),

                html.Div(
                    [
                        html.Div(
                            dcc.Slider(
                                id="month-slider",
                                min=0,
                                max=LATEST_MONTH_INDEX,
                                step=1,
                                value=LATEST_MONTH_INDEX,
                                # Every 5th year, plus whichever is
                                # latest even if not a multiple of 5 -
                                # a mark per year (25 of them) was
                                # illegibly cramped into this width.
                                # The exact year is still always known
                                # from the handle's own position/the
                                # pyramid's title, so sparse marks are
                                # just orientation, not the only cue.
                                marks={
                                    i: month[:4]
                                    for i, month in enumerate(
                                        AVAILABLE_MONTHS
                                    )
                                    if int(month[:4]) % 5 == 0
                                    or i == LATEST_MONTH_INDEX
                                },
                                allow_direct_input=False,
                            ),
                            style={"flex": "1 1 auto"},
                        ),
                        html.Button("Play", id="play-button", n_clicks=0),
                        # Renders nothing; just fires on a timer while
                        # not disabled.
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
                        "padding": "0.75rem 1rem",
                        "flex": "0 0 auto",
                    },
                ),
            ],
            style={
                "flex": "1 1 40%",
                "display": "flex",
                "flexDirection": "column",
                "minWidth": 0,
                "minHeight": 0,
                # Bottom padding clears Dash's own dev-mode debug menu
                # (bottom-right "Callbacks/Errors/..." bar, shown when
                # app.run(debug=True)), which otherwise overlaps the
                # year controls sitting flush with the viewport bottom.
                "padding": "0 1rem 4.5rem 1rem",
                "overflow": "hidden",
            },
        ),
    ],
    style={
        "height": "100vh",
        "display": "flex",
        "overflow": "hidden",
        "fontFamily": "system-ui, -apple-system, 'Segoe UI', sans-serif",
    },
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
    Output("boundaries-layer", "data"),
    Input("level-selector", "value"),
)
def update_boundaries_layer(level: str) -> dict:
    """Switch the map's border layer between municipalities and counties.

    Args:
        level: "municipality" or "county" (the level-selector's value).

    Returns:
        COUNTIES_GEOJSON at "county", otherwise MUNICIPALITIES_GEOJSON.
    """
    return COUNTIES_GEOJSON if level == "county" else MUNICIPALITIES_GEOJSON


@app.callback(
    Output("in-radius-layer", "data"),
    Output("selected-area-layer", "data"),
    Input("map", "center"),
    Input("radius-slider", "value"),
    Input("level-selector", "value"),
)
def update_boundary_highlights(
    center: dict | None,
    radius_slider_value: float,
    level: str,
) -> tuple[dict, dict]:
    """Highlight in-radius areas and the one the pin is actually inside.

    Args:
        center: The map's current center, as {"lat": ..., "lng": ...},
            or None before the map has reported one.
        radius_slider_value: The radius-slider's raw (log-scale) value.
        level: "municipality" or "county" (the level-selector's value).

    Returns:
        A (in_radius_geojson, selected_geojson) pair: the first holds
        every area within the radius except the one containing the
        selected point, the second holds just that containing area (or
        both are empty FeatureCollections if center is None or nothing
        matches).
    """
    if not center:
        return EMPTY_GEOJSON, EMPTY_GEOJSON

    radius_km = radius_slider_value_to_km(radius_slider_value)

    if level == "county":
        areas = find_counties_within_radius(
            latitude=center["lat"],
            longitude=center["lng"],
            radius_km=radius_km,
            geojson=MUNICIPALITIES_GEOJSON,
        )
        id_key = "lan_code"
        source_geojson = COUNTIES_GEOJSON
        feature_id_key = "lan_code"
    else:
        areas = find_municipalities_within_radius(
            latitude=center["lat"],
            longitude=center["lng"],
            radius_km=radius_km,
            geojson=MUNICIPALITIES_GEOJSON,
        )
        id_key = "region_code"
        source_geojson = MUNICIPALITIES_GEOJSON
        feature_id_key = "id"

    selected_ids = {
        area[id_key] for area in areas if area["contains_point"]
    }
    in_radius_ids = {
        area[id_key] for area in areas if area[id_key] not in selected_ids
    }

    in_radius_features = [
        feature
        for feature in source_geojson["features"]
        if feature["properties"][feature_id_key] in in_radius_ids
    ]
    selected_features = [
        feature
        for feature in source_geojson["features"]
        if feature["properties"][feature_id_key] in selected_ids
    ]

    return (
        {"type": "FeatureCollection", "features": in_radius_features},
        {"type": "FeatureCollection", "features": selected_features},
    )


@app.callback(
    Output("radius-ring", "style"),
    Input("map", "center"),
    Input("map", "zoom"),
    Input("radius-slider", "value"),
)
def update_radius_ring(
    center: dict | None,
    zoom: int | None,
    radius_slider_value: float,
) -> dict:
    """Resize the fixed-screen radius ring to match the selected radius.

    The ring's position never lags behind a map drag (see module
    docstring) since it's screen-fixed by construction; only its
    pixel size needs recomputing here, from the selected radius and
    the map's current zoom/latitude.

    Args:
        center: The map's current center, as {"lat": ..., "lng": ...},
            or None before the map has reported one.
        zoom: The map's current zoom level, or None before reported.
        radius_slider_value: The radius-slider's raw (log-scale) value.

    Returns:
        RADIUS_RING_BASE_STYLE with width/height set to the radius's
        current on-screen pixel diameter.
    """
    latitude = center["lat"] if center else INITIAL_LAT
    radius_km = radius_slider_value_to_km(radius_slider_value)
    diameter_px = 2 * radius_km_to_px(
        radius_km, latitude, zoom or INITIAL_ZOOM
    )

    return {
        **RADIUS_RING_BASE_STYLE,
        "width": f"{diameter_px}px",
        "height": f"{diameter_px}px",
    }


@app.callback(
    Output("radius-label", "children"),
    Input("radius-slider", "value"),
)
def update_radius_label(radius_slider_value: float) -> str:
    """Show the current radius in kilometers next to its slider.

    Args:
        radius_slider_value: The radius-slider's raw (log-scale) value.

    Returns:
        "Radius: {km} km".
    """
    return f"Radius: {radius_slider_value_to_km(radius_slider_value)} km"


@app.callback(
    Output("population-pyramid", "figure"),
    Input("map", "center"),
    Input("radius-slider", "value"),
    Input("month-slider", "value"),
    Input("level-selector", "value"),
)
def update_population_pyramid(
    center: dict | None,
    radius_slider_value: float,
    month_index: int,
    level: str,
) -> go.Figure:
    """Build the population pyramid for the selected area and year.

    Args:
        center: The map's current center, as {"lat": ..., "lng": ...},
            or None before the map has reported one.
        radius_slider_value: The radius-slider's raw (log-scale) value.
        month_index: Index into AVAILABLE_MONTHS for the selected year.
        level: "municipality" or "county" (the level-selector's value).
            At "county", the pyramid covers every municipality in each
            matched county, not just the ones inside the radius.

    Returns:
        The population pyramid for the selected areas and year (empty
        if center is None or nothing matches), titled with the nearest
        area names (see _summarize_areas) - the year is already shown
        by the year slider itself, so it isn't repeated here - with
        the x-axis fixed to the largest value seen across every year
        of the current selection so it doesn't rescale as the year
        slider or play/pause moves through months.
    """
    month = AVAILABLE_MONTHS[month_index]
    areas: list[dict] = []
    region_codes: list[str] = []
    name_key = "region"

    if center:
        radius_km = radius_slider_value_to_km(radius_slider_value)

        if level == "county":
            areas = find_counties_within_radius(
                latitude=center["lat"],
                longitude=center["lng"],
                radius_km=radius_km,
                geojson=MUNICIPALITIES_GEOJSON,
            )
            name_key = "county"
            region_codes = [
                code for area in areas for code in area["region_codes"]
            ]
        else:
            areas = find_municipalities_within_radius(
                latitude=center["lat"],
                longitude=center["lng"],
                radius_km=radius_km,
                geojson=MUNICIPALITIES_GEOJSON,
            )
            region_codes = [area["region_code"] for area in areas]

    title = _summarize_areas(areas, name_key)

    if region_codes:
        pyramid_data = get_population_pyramid(region_codes, month)
        axis_max = get_max_pyramid_value(region_codes)
        return create_population_pyramid(
            pyramid_data, axis_max=axis_max, title=title
        )

    return create_population_pyramid(EMPTY_PYRAMID_DATA, title=title)


if __name__ == "__main__":
    app.run(debug=True)
