import pandas as pd

from scb_data.queries import (
    get_population_by_region,
    get_population_change,
)
from scb_data.database import insert_population_data

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