"""Tests for scb_data.visualisation."""

import pandas as pd
import plotly.graph_objects as go
import pytest

from scb_data.visualisation import (
    create_migration_sankey,
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
    assert "Simple model" in caption


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


def _migration_flows_fixture():
    return pd.DataFrame(
        {
            "lan_code": ["03", "04", "05"],
            "inflow": [150, 0, 30],
            "outflow": [100, 50, 0],
        }
    )


def test_create_migration_sankey_returns_figure():
    fig = create_migration_sankey(
        _migration_flows_fixture(), direction="to", area_label="Selected"
    )

    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
    assert isinstance(fig.data[0], go.Sankey)


def test_create_migration_sankey_to_direction_points_at_selected_area():
    fig = create_migration_sankey(
        _migration_flows_fixture(), direction="to", area_label="Selected"
    )

    sankey = fig.data[0]

    # Only 03 (150) and 05 (30) have nonzero inflow; 04 (0) is excluded.
    # "Selected area" is always node 0; other counties fill in after it,
    # each labeled with its own value.
    assert list(sankey.node.label[1:]) == [
        "Uppsala län (150)", "Östergötlands län (30)",
    ]
    assert all(target == 0 for target in sankey.link.target)
    assert list(sankey.link.value) == [150, 30]


def test_create_migration_sankey_disables_dragging_and_hover():
    fig = create_migration_sankey(
        _migration_flows_fixture(), direction="to", area_label="Selected"
    )

    sankey = fig.data[0]

    assert sankey.arrangement == "fixed"
    assert sankey.node.hoverinfo == "skip"
    assert sankey.link.hoverinfo == "skip"


def test_create_migration_sankey_folds_extra_counties_into_other():
    data = pd.DataFrame(
        {
            "lan_code": [f"{i:02d}" for i in range(1, 15)],
            "inflow": list(range(140, 0, -10)),
            "outflow": [0] * 14,
        }
    )

    fig = create_migration_sankey(
        data, direction="to", area_label="Selected", max_other_counties=10
    )

    sankey = fig.data[0]

    # 1 selected-area node + 10 individual counties + 1 "Other" node.
    assert len(sankey.node.label) == 12
    assert sankey.node.label[-1].startswith("Other counties (4)")

    # The folded total is the sum of the 4 smallest flows (40+30+20+10).
    assert list(sankey.link.value)[-1] == 100


def test_create_migration_sankey_from_direction_points_away():
    fig = create_migration_sankey(
        _migration_flows_fixture(), direction="from", area_label="Selected"
    )

    sankey = fig.data[0]

    # Only 03 (100) and 04 (50) have nonzero outflow; 05 (0) is excluded.
    assert all(source == 0 for source in sankey.link.source)
    assert list(sankey.link.value) == [100, 50]


def test_create_migration_sankey_sorts_largest_flow_first():
    fig = create_migration_sankey(
        _migration_flows_fixture(), direction="to", area_label="Selected"
    )

    values = list(fig.data[0].link.value)

    assert values == sorted(values, reverse=True)


def test_create_migration_sankey_selected_area_is_first_node():
    fig = create_migration_sankey(
        _migration_flows_fixture(),
        direction="to",
        area_label="Västra Götaland",
    )

    # Labeled with the total of its own flows (150 + 30 inflow).
    assert fig.data[0].node.label[0] == "Västra Götaland (180)"


def test_create_migration_sankey_handles_empty_data():
    fig = create_migration_sankey(
        pd.DataFrame(columns=["lan_code", "inflow", "outflow"]),
        direction="to",
        area_label="Selected",
    )

    sankey = fig.data[0]

    assert list(sankey.node.label) == ["Selected (0)"]
    assert len(sankey.link.value) == 0


def test_create_migration_sankey_sets_title_when_given():
    fig = create_migration_sankey(
        _migration_flows_fixture(),
        direction="to",
        area_label="Selected",
        title="Selected — moved to (2024)",
    )

    assert fig.layout.title.text == "Selected — moved to (2024)"
