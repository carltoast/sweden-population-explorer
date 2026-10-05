"""Tests for scb_data.queries (require a running Postgres instance)."""

import pandas as pd

from scb_data.database import insert_migration_data, insert_population_data
from scb_data.queries import (
    get_available_months,
    get_max_pyramid_value,
    get_migration_flows,
    get_population_pyramid,
    get_population_trend,
)


def test_get_available_months():
    df = pd.DataFrame(
        {
            "region_code": ["1480", "1480", "1480"],
            "region": ["Göteborg", "Göteborg", "Göteborg"],
            "age_code": ["-9", "-9", "-9"],
            "age_group": ["0–9 years", "0–9 years", "0–9 years"],
            "sex_code": ["1", "1", "1"],
            "sex": ["men", "men", "men"],
            "month": ["2023M12", "2022M12", "2024M12"],
            "population": [100, 90, 110],
        }
    )

    insert_population_data(df)

    assert get_available_months() == ["2022M12", "2023M12", "2024M12"]


def test_get_population_pyramid():
    df = pd.DataFrame(
        {
            "region_code": ["1480", "1480", "1481", "1481", "0180"],
            "region": [
                "Göteborg", "Göteborg", "Mölndal", "Mölndal", "Stockholm",
            ],
            "age_code": ["-9", "-9", "-9", "-9", "-9"],
            "age_group": [
                "0–9 years",
                "0–9 years",
                "0–9 years",
                "0–9 years",
                "0–9 years",
            ],
            "sex_code": ["1", "2", "1", "2", "1"],
            "sex": ["men", "women", "men", "women", "men"],
            "month": [
                "2024M12",
                "2024M12",
                "2024M12",
                "2024M12",
                "2024M12",
            ],
            "population": [100, 90, 20, 15, 99999],
        }
    )

    insert_population_data(df)

    result = get_population_pyramid(
        region_codes=["1480", "1481"],
        month="2024M12",
    )

    assert list(result.columns) == [
        "age_code",
        "age_group",
        "sex_code",
        "sex",
        "population",
    ]

    # Stockholm excluded, Göteborg + Mölndal summed by sex.
    assert len(result) == 2

    men = result[result["sex_code"] == "1"].iloc[0]
    women = result[result["sex_code"] == "2"].iloc[0]

    assert men["population"] == 120
    assert women["population"] == 105


def test_get_population_pyramid_orders_by_age():
    df = pd.DataFrame(
        {
            "region_code": ["1480", "1480", "1480"],
            "region": ["Göteborg", "Göteborg", "Göteborg"],
            "age_code": ["100+", "-9", "20-29"],
            "age_group": ["100+ years", "0–9 years", "20–29 years"],
            "sex_code": ["1", "1", "1"],
            "sex": ["men", "men", "men"],
            "month": ["2024M12", "2024M12", "2024M12"],
            "population": [10, 20, 30],
        }
    )

    insert_population_data(df)

    result = get_population_pyramid(
        region_codes=["1480"],
        month="2024M12",
    )

    assert list(result["age_code"]) == ["-9", "20-29", "100+"]


def test_get_population_trend_sums_across_regions_by_month():
    df = pd.DataFrame(
        {
            "region_code": ["1480", "1480", "1481", "1481", "0180"],
            "region": [
                "Göteborg", "Göteborg", "Mölndal", "Mölndal", "Stockholm",
            ],
            "age_code": ["-9", "-9", "-9", "-9", "-9"],
            "age_group": [
                "0–9 years",
                "0–9 years",
                "0–9 years",
                "0–9 years",
                "0–9 years",
            ],
            "sex_code": ["1", "1", "1", "1", "1"],
            "sex": ["men", "men", "men", "men", "men"],
            "month": [
                "2020M12",
                "2024M12",
                "2020M12",
                "2024M12",
                "2024M12",
            ],
            "population": [100, 110, 20, 25, 99999],
        }
    )

    insert_population_data(df)

    result = get_population_trend(region_codes=["1480", "1481"])

    assert list(result.columns) == ["month", "population"]
    assert list(result["month"]) == ["2020M12", "2024M12"]
    assert list(result["population"]) == [120, 135]


def test_get_population_trend_empty_for_no_matching_regions():
    result = get_population_trend(region_codes=["9999"])

    assert list(result.columns) == ["month", "population"]
    assert len(result) == 0


def test_get_max_pyramid_value_finds_largest_age_sex_total_across_months():
    df = pd.DataFrame(
        {
            "region_code": ["1480", "1480", "1480", "1480"],
            "region": ["Göteborg", "Göteborg", "Göteborg", "Göteborg"],
            "age_code": ["-9", "-9", "20-29", "20-29"],
            "age_group": [
                "0–9 years", "0–9 years", "20–29 years", "20–29 years",
            ],
            "sex_code": ["1", "1", "1", "1"],
            "sex": ["men", "men", "men", "men"],
            "month": ["2020M12", "2024M12", "2020M12", "2024M12"],
            "population": [100, 150, 200, 90],
        }
    )

    insert_population_data(df)

    assert get_max_pyramid_value(["1480"]) == 200


def test_get_max_pyramid_value_returns_zero_for_no_matching_regions():
    assert get_max_pyramid_value(["9999"]) == 0.0


def _migration_fixture():
    return pd.DataFrame(
        {
            "from_lan_code": ["01", "03", "01", "05", "03", "04"],
            "to_lan_code": ["03", "01", "04", "01", "04", "03"],
            "sex_code": ["1", "1", "1", "1", "1", "1"],
            "year": ["2024"] * 6,
            "migrations": [100, 150, 50, 30, 999, 20],
        }
    )


def test_get_migration_flows_single_county():
    insert_migration_data(_migration_fixture())

    result = get_migration_flows(lan_codes=["01"], year="2024")

    assert list(result.columns) == ["lan_code", "inflow", "outflow"]

    by_county = result.set_index("lan_code")
    # 03 <-> 04 (999) touches neither endpoint of the "01" selection and
    # is correctly excluded entirely.
    assert by_county.loc["03", "inflow"] == 150
    assert by_county.loc["03", "outflow"] == 100
    assert by_county.loc["04", "inflow"] == 0
    assert by_county.loc["04", "outflow"] == 50
    assert by_county.loc["05", "inflow"] == 30
    assert by_county.loc["05", "outflow"] == 0
    assert "01" not in by_county.index


def test_get_migration_flows_excludes_internal_multi_county_flows():
    insert_migration_data(_migration_fixture())

    result = get_migration_flows(lan_codes=["01", "03"], year="2024")

    by_county = result.set_index("lan_code")
    # 01<->03 (100, 150) is internal to the selection and excluded;
    # 03->04 (999) and 01->04 (50) both count as outflow from the
    # selected area since 04 isn't selected.
    assert by_county.loc["04", "outflow"] == 999 + 50
    assert by_county.loc["04", "inflow"] == 20
    assert by_county.loc["05", "inflow"] == 30
    assert by_county.loc["05", "outflow"] == 0
    assert "01" not in by_county.index
    assert "03" not in by_county.index


def test_get_migration_flows_empty_for_no_counties():
    result = get_migration_flows(lan_codes=[], year="2024")

    assert list(result.columns) == ["lan_code", "inflow", "outflow"]
    assert len(result) == 0
