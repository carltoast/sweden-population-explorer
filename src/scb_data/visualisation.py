"""Plotly figure: the population pyramid."""

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
