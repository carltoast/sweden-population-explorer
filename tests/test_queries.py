"""Tests for scb_data.queries (require a running Postgres instance)."""

import pandas as pd

from scb_data.database import insert_population_data
from scb_data.queries import (
    get_available_months,
    get_max_pyramid_value,
    get_population_by_region,
    get_population_change,
    get_population_history,
    get_population_pyramid,
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


def test_get_population_by_region():
    df = pd.DataFrame(
        {
            "region_code": ["0180", "1480", "1481"],
            "region": ["Stockholm", "Göteborg", "Mölndal"],
            "age_code": ["-9", "-9", "-9"],
            "age_group": ["0–9 years", "0–9 years", "0–9 years"],
            "sex_code": ["1", "1", "1"],
            "sex": ["men", "men", "men"],
            "month": ["2024M12", "2024M12", "2024M12"],
            "population": [53207, 32925, 10000],
        }
    )

    insert_population_data(df)
    result = get_population_by_region("2024M12")

    assert len(result) == 3
    assert list(result.columns) == [
        "region_code",
        "region",
        "population",
    ]

    assert result.iloc[0]["region"] == "Stockholm"
    assert result.iloc[0]["population"] == 53207


def test_get_population_change():
    df = pd.DataFrame(
        {
            "region_code": [
                "0180",
                "0180",
                "0180",
                "1480",
                "1480",
            ],
            "region": [
                "Stockholm",
                "Stockholm",
                "Stockholm",
                "Göteborg",
                "Göteborg",
            ],
            "age_code": [
                "-9",
                "-9",
                "-9",
                "-9",
                "-9",
            ],
            "age_group": [
                "0–9 years",
                "0–9 years",
                "0–9 years",
                "0–9 years",
                "0–9 years",
            ],
            "sex_code": [
                "1",
                "1",
                "1",
                "1",
                "1",
            ],
            "sex": [
                "men",
                "men",
                "men",
                "men",
                "men",
            ],
            "month": [
                "2022M12",
                "2023M12",
                "2024M12",
                "2023M12",
                "2024M12",
            ],
            "population": [
                10000,
                10500,
                11000,
                5000,
                5500,
            ],
        }
    )

    insert_population_data(df)

    result = get_population_change("2024M12")

    assert len(result) == 5

    assert list(result.columns) == [
        "region_code",
        "region",
        "month",
        "population",
        "population_change",
    ]

    # Stockholm
    stockholm = result[result["region_code"] == "0180"]

    assert stockholm.iloc[0]["population"] == 10000
    assert pd.isna(stockholm.iloc[0]["population_change"])

    assert stockholm.iloc[1]["population"] == 10500
    assert stockholm.iloc[1]["population_change"] == 500

    assert stockholm.iloc[2]["population"] == 11000
    assert stockholm.iloc[2]["population_change"] == 500

    # Göteborg
    goteborg = result[result["region_code"] == "1480"]

    assert goteborg.iloc[0]["population"] == 5000
    assert pd.isna(goteborg.iloc[0]["population_change"])

    assert goteborg.iloc[1]["population"] == 5500
    assert goteborg.iloc[1]["population_change"] == 500


def test_get_population_history():
    df = pd.DataFrame(
        {
            "region_code": [
                "1480",
                "1480",
                "1480",
                "0180",
            ],
            "region": [
                "Göteborg",
                "Göteborg",
                "Göteborg",
                "Stockholm",
            ],
            "age_code": [
                "-9",
                "-9",
                "-9",
                "-9",
            ],
            "age_group": [
                "0–9 years",
                "0–9 years",
                "0–9 years",
                "0–9 years",
            ],
            "sex_code": [
                "1",
                "1",
                "1",
                "1",
            ],
            "sex": [
                "men",
                "men",
                "men",
                "men",
            ],
            "month": [
                "2024M10",
                "2024M11",
                "2024M12",
                "2024M12",
            ],
            "population": [
                5000,
                5200,
                5500,
                10000,
            ],
        }
    )

    insert_population_data(df)

    result = get_population_history(
        region_code="1480",
        end_month="2024M12",
    )

    assert len(result) == 3

    assert list(result.columns) == [
        "month",
        "population",
    ]

    assert list(result["month"]) == [
        "2024M10",
        "2024M11",
        "2024M12",
    ]

    assert list(result["population"]) == [
        5000,
        5200,
        5500,
    ]


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
