"""Tests for scb_data.visualisation."""

import pandas as pd
import plotly.graph_objects as go
import pytest

from scb_data.visualisation import (
    create_population_pyramid,
    create_population_trend,
)


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


def test_create_population_pyramid_sets_title_when_given():
    fig = create_population_pyramid(
        _population_pyramid_fixture(), title="Göteborg<br>2024M12"
    )

    assert fig.layout.title.text == "Göteborg<br>2024M12"


def test_create_population_pyramid_has_no_title_by_default():
    fig = create_population_pyramid(_population_pyramid_fixture())

    assert fig.layout.title.text is None


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


def _population_trend_fixture():
    return pd.DataFrame(
        {
            "month": ["2020M12", "2022M12", "2024M12"],
            "population": [1000, 1100, 1210],
        }
    )


def test_create_population_trend_returns_figure():
    fig = create_population_trend(_population_trend_fixture())

    assert isinstance(fig, go.Figure)


def test_create_population_trend_historical_trace_matches_input():
    fig = create_population_trend(_population_trend_fixture())

    historical = next(
        trace for trace in fig.data if trace.name == "Historical"
    )

    assert list(historical.x) == [2020, 2022, 2024]
    assert list(historical.y) == [1000, 1100, 1210]


def test_create_population_trend_projects_forward():
    fig = create_population_trend(
        _population_trend_fixture(), projection_years=5
    )

    projected = next(
        trace for trace in fig.data if trace.name == "Projected"
    )

    # Starts at the last historical year and runs projection_years past
    # it, growing (this fixture's population increases every period).
    assert projected.x[0] == 2024
    assert projected.x[-1] == 2029
    assert projected.y[-1] > projected.y[0]


def test_create_population_trend_projection_has_no_jump():
    # The projection must start exactly at the last historical value -
    # anchoring to the regression line's own (generally different)
    # fitted value there instead caused a visible discontinuity.
    fig = create_population_trend(_population_trend_fixture())

    historical = next(
        trace for trace in fig.data if trace.name == "Historical"
    )
    projected = next(
        trace for trace in fig.data if trace.name == "Projected"
    )

    assert projected.x[0] == historical.x[-1]
    assert projected.y[0] == pytest.approx(historical.y[-1])


def test_create_population_trend_no_projection_with_one_point():
    data = pd.DataFrame({"month": ["2024M12"], "population": [1000]})

    fig = create_population_trend(data)

    assert not any(trace.name == "Projected" for trace in fig.data)
    assert len(fig.layout.annotations) == 0


def test_create_population_trend_caption_states_rate_and_year_range():
    fig = create_population_trend(_population_trend_fixture())

    assert len(fig.layout.annotations) == 1

    caption = fig.layout.annotations[0].text

    assert caption.startswith("Projection:")
    assert "%/year compound growth" in caption
    assert "fit to 2020–2024 data" in caption


def test_create_population_trend_handles_empty_data():
    fig = create_population_trend(
        pd.DataFrame(columns=["month", "population"])
    )

    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 0


def test_create_population_trend_sets_title_when_given():
    fig = create_population_trend(
        _population_trend_fixture(), title="Göteborg"
    )

    assert fig.layout.title.text == "Göteborg"
