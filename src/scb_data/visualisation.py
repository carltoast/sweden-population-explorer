"""Plotly figures: the population pyramid, trend, and migration Sankey."""

import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from scb_data.geography import COUNTY_NAMES

# Aqua/violet (categorical slots 3 and 7): a gender-neutral pair, re-checked
# against the dataviz skill's validator for this specific (non-adjacent)
# pairing since the palette only pre-validates adjacent slots - CVD Delta E
# 31.1, normal-vision Delta E 35.8 (target/floor 8.0/15.0), both well clear.
# Aqua's contrast against white is 2.74 (just under the 3:1 floor); the
# palette's documented mitigation for that - visible direct labels - is
# already satisfied by this chart's legend and hover labels.
MALE_COLOR = "#1baf7a"
FEMALE_COLOR = "#4a3aa7"

# Categorical slot 1 (blue): unused elsewhere in this app (the pyramid uses
# slots 3/7 above), so the trend chart reads as visually distinct from it
# rather than implying some relationship between the two charts' colors.
TREND_COLOR = "#2a78d6"


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
    title: str | None = None,
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
        title: Optional title text, set here (rather than via a
            separate fig.update_layout call from the caller) so its
            top margin stays coordinated with the rest of the layout
            in one place. Defaults to None (no title), used as-is by
            callers that don't need one (e.g. tests).

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

    layout: dict = {
        "barmode": "overlay",
        "xaxis": {
            "title": "Population",
            "range": [tick_values[0], tick_values[-1]],
            "tickvals": tick_values,
            "ticktext": tick_text,
            "gridcolor": "#e1e0d9",
            "zerolinecolor": "#c3c2b7",
        },
        "yaxis": {"title": "Age group"},
        "plot_bgcolor": "white",
        "paper_bgcolor": "white",
        # Inside the plot area (top-left corner, over the oldest/usually
        # shortest bars) rather than above it - saves the vertical space
        # a separate legend row would take, and a title only needs a
        # single line of top margin now that they no longer share it.
        "legend": {
            "x": 0.02,
            "y": 0.98,
            "xanchor": "left",
            "yanchor": "top",
            "bgcolor": "rgba(255, 255, 255, 0.7)",
        },
        "margin": {"t": 50},
    }

    if title:
        layout["title"] = {"text": title, "x": 0.5}

    fig.update_layout(**layout)

    return fig


def create_population_trend(
    data: pd.DataFrame,
    projection_years: int = 10,
    title: str | None = None,
) -> go.Figure:
    """Create a population-over-time line chart with a growth projection.

    Args:
        data: Rows with month ("YYYYMmm") and population (summed
            across the selected areas, e.g. from
            scb_data.queries.get_population_trend), ordered
            chronologically. May be empty.
        projection_years: How many years beyond the last available
            year to project forward. Defaults to 10.
        title: Optional title text (see create_population_pyramid's
            title parameter for why it's built in here).

    Returns:
        A figure with a solid historical line plus, if there are at
        least two historical points, a dashed projected continuation.
        The growth rate is fit via linear regression of ln(population)
        against year (so the projection compounds, like interest,
        rather than extrapolating a constant absolute change - a
        better fit for population growth, which tends to be
        multiplicative, than a plain linear extrapolation would be),
        but the curve itself is anchored to the last *actual* observed
        value rather than the regression's own fitted value there -
        anchoring to the regression line directly produced a visible
        jump at the historical/projected boundary whenever the
        least-squares fit (pulled toward every historical point, not
        just the last one) didn't pass exactly through the latest
        year's real figure, which was often enough to look broken.
        Whenever there's a projection, a caption annotation below the
        chart states the actual fitted annual growth rate and the
        historical year range it was fit to, so the projection isn't
        an unexplained black box.
    """
    fig = go.Figure()
    caption = None

    if not data.empty:
        years = data["month"].str[:4].astype(int)
        population = data["population"].astype(float)

        fig.add_trace(
            go.Scatter(
                x=years,
                y=population,
                mode="lines+markers",
                name="Historical",
                line={"color": TREND_COLOR},
                hovertemplate="%{x}<br>%{y:,.0f}<extra></extra>",
            )
        )

        if len(years) >= 2 and (population > 0).all():
            growth_rate, _ = np.polyfit(years, np.log(population), 1)
            last_year = years.iloc[-1]
            last_population = population.iloc[-1]
            future_years = np.arange(
                last_year, last_year + projection_years + 1
            )
            projected = last_population * np.exp(
                growth_rate * (future_years - last_year)
            )

            fig.add_trace(
                go.Scatter(
                    x=future_years,
                    y=projected,
                    mode="lines",
                    name="Projected",
                    line={"color": TREND_COLOR, "dash": "dash"},
                    hovertemplate=(
                        "%{x}<br>%{y:,.0f} (projected)<extra></extra>"
                    ),
                )
            )

            # The actual fitted rate, not just the method's name, so the
            # projection isn't a black box - a reader can judge for
            # themselves whether +1.3%/year sounds like a reasonable
            # continuation of the trend they're looking at.
            annual_growth_pct = (math.exp(growth_rate) - 1) * 100
            caption = (
                f"Projection: {annual_growth_pct:+.1f}%/year compound "
                f"growth, fit to {years.iloc[0]}–{last_year} data"
            )

    layout: dict = {
        "xaxis": {
            "title": "Year",
            "gridcolor": "#e1e0d9",
            "zerolinecolor": "#c3c2b7",
        },
        "yaxis": {
            "title": "Population",
            "tickformat": ",",
            "gridcolor": "#e1e0d9",
            "zerolinecolor": "#c3c2b7",
        },
        "plot_bgcolor": "white",
        "paper_bgcolor": "white",
        "legend": {
            "x": 0.02,
            "y": 0.98,
            "xanchor": "left",
            "yanchor": "top",
            "bgcolor": "rgba(255, 255, 255, 0.7)",
        },
        # Extra bottom margin makes room for the caption annotation
        # below the x-axis title, when there is one (harmless unused
        # space otherwise). The annotation's "paper"-relative y is a
        # *fraction of the plot area's height*, not a pixel offset, so
        # it was initially placed far enough below the axis to fall
        # outside a too-small margin and get silently clipped - a
        # generous fixed margin plus a shallower fraction keeps it
        # inside the figure regardless of the plot's actual height.
        "margin": {"t": 50, "b": 120},
    }

    if title:
        layout["title"] = {"text": title, "x": 0.5}

    if caption:
        layout["annotations"] = [
            {
                "text": caption,
                "showarrow": False,
                "xref": "paper",
                "yref": "paper",
                "x": 0.5,
                "y": -0.13,
                "xanchor": "center",
                "yanchor": "top",
                "font": {"size": 12, "color": "#898781"},
            }
        ]

    fig.update_layout(**layout)

    return fig


# This is an "emphasis" diagram, not a categorical one: the selected area is
# the one subject the reader cares about, every other county is context, not
# a set of identities that each need their own distinct hue (a rainbow
# Sankey would wrongly imply the individual county colors mean something -
# the real magnitude encoding is link width/the hover value, not color). One
# accent (amber, matching the map's selected-area highlight - see app.py's
# SELECTED_AREA_STYLE) plus one muted neutral for every "other" node and
# link keeps the two roles (subject vs. context) clear without a false
# categorical distinction between the other counties.
SANKEY_SELECTED_COLOR = "#f2a900"
SANKEY_OTHER_COLOR = "#c3c2b7"
SANKEY_LINK_COLOR = "rgba(242, 169, 0, 0.35)"


def create_migration_sankey(
    data: pd.DataFrame,
    direction: str,
    area_label: str,
    title: str | None = None,
) -> go.Figure:
    """Create a Sankey diagram of migration flows in/out of a selection.

    Args:
        data: Rows with lan_code, inflow, and outflow (e.g. from
            scb_data.queries.get_migration_flows), one row per other
            county with a nonzero flow in either direction. May be
            empty.
        direction: "to" shows migrations *into* the selected area (an
            arrow per other county, pointing at the selected area,
            sized by that county's outflow to it); "from" shows
            migrations *out of* the selected area (arrows pointing
            away from it, sized by its outflow to each other county).
        area_label: Display name for the aggregate selected-area node
            (e.g. the pyramid tab's own area summary).
        title: Optional title text (see create_population_pyramid's
            title parameter for why it's built in here).

    Returns:
        A Sankey figure with the selected area as one node (amber)
        and one node per other county with a nonzero flow in the
        requested direction (muted gray), sorted so the largest flows
        are easiest to pick out. Link width is proportional to the
        number of migrations. Just the "Selected area" node, with no
        links, if data is empty or every flow in the requested
        direction is zero.
    """
    value_column = "inflow" if direction == "to" else "outflow"
    flows = data[data[value_column] > 0].sort_values(
        value_column, ascending=False
    )

    county_labels = [
        COUNTY_NAMES.get(code, code) for code in flows["lan_code"]
    ]
    node_labels = [area_label] + county_labels
    node_colors = [SANKEY_SELECTED_COLOR] + [SANKEY_OTHER_COLOR] * len(
        county_labels
    )
    other_node_indices = list(range(1, len(node_labels)))

    if direction == "to":
        # other county -> selected area
        sources = other_node_indices
        targets = [0] * len(county_labels)
    else:
        # selected area -> other county
        sources = [0] * len(county_labels)
        targets = other_node_indices

    fig = go.Figure(
        go.Sankey(
            node={
                "label": node_labels,
                "color": node_colors,
                "pad": 16,
                "thickness": 18,
                "line": {"width": 0},
            },
            link={
                "source": sources,
                "target": targets,
                "value": list(flows[value_column]),
                "color": SANKEY_LINK_COLOR,
                "hovertemplate": (
                    "%{source.label} → %{target.label}"
                    "<br>%{value:,.0f} people<extra></extra>"
                ),
            },
        )
    )

    layout: dict = {
        "font": {"size": 13, "color": "#52514e"},
        "paper_bgcolor": "white",
        "margin": {"t": 50, "l": 10, "r": 10, "b": 10},
    }

    if title:
        layout["title"] = {"text": title, "x": 0.5}

    fig.update_layout(**layout)

    return fig
