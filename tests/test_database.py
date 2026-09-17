"""Tests for scb_data.database (require a running Postgres instance)."""

import pandas as pd

from scb_data.database import (
    check_connection,
    clear_population_table,
    create_population_table,
    get_population_count,
    insert_population_data,
)


def test_check_connection():
    assert check_connection() == 1


def test_insert_population_data():
    df = pd.DataFrame(
        {
            "region_code": ["0180", "1480"],
            "region": ["Stockholm", "Göteborg"],
            "age_code": ["-9", "-9"],
            "age_group": ["0–9 years", "0–9 years"],
            "sex_code": ["1", "2"],
            "sex": ["men", "women"],
            "month": ["2024M12", "2024M12"],
            "population": [53207, 50603],
        }
    )

    clear_population_table()
    create_population_table()
    insert_population_data(df)

    assert get_population_count() == 2
