"""Tests for scb_data.queries (require a running Postgres instance)."""

import pandas as pd

from scb_data.database import insert_population_data
from scb_data.queries import (
    get_available_months,
    get_max_pyramid_value,
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
