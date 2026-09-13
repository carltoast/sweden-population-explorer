import pandas as pd
import plotly.graph_objects as go


def prepare_geojson(geojson: dict) -> dict:
    """Prepare municipality GeoJSON for Plotly rendering."""
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


def add_municipality_boundaries(
    fig: go.Figure,
    geojson: dict,
) -> None:
    """Add municipality boundaries to a Plotly geographic figure."""
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


def create_population_map(
    data: pd.DataFrame,
    geojson: dict,
) -> go.Figure:
    """Create a choropleth map of municipal population."""

    data = data.copy()
    data["municipality_code"] = data["municipality_code"].astype(str)

    plotly_geojson = prepare_geojson(geojson)

    fig = go.Figure(
        go.Choropleth(
            geojson=plotly_geojson,
            locations=data["municipality_code"],
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
            customdata=data["municipality_name"],
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