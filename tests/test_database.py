"""Tests for scb_data.database (require a running Postgres instance)."""

import pandas as pd

from scb_data.database import (
    clear_population_table,
    create_population_table,
    get_connection,
    insert_population_data,
)


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

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM population;")
            row_count = cursor.fetchone()[0]

    assert row_count == 2
