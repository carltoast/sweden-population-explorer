"""Tests for scb_data.database (require a running Postgres instance)."""

import pandas as pd

from scb_data.database import (
    clear_migration_table,
    clear_population_table,
    create_migration_table,
    create_population_table,
    get_connection,
    insert_migration_data,
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


def test_insert_migration_data():
    df = pd.DataFrame(
        {
            "from_lan_code": ["01", "03"],
            "to_lan_code": ["03", "01"],
            "sex_code": ["1", "1"],
            "year": ["2024", "2024"],
            "migrations": [3517, 1927],
        }
    )

    clear_migration_table()
    create_migration_table()
    insert_migration_data(df)

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM migration;")
            row_count = cursor.fetchone()[0]

    assert row_count == 2


def test_insert_migration_data_upserts_on_conflict():
    df = pd.DataFrame(
        {
            "from_lan_code": ["01"],
            "to_lan_code": ["03"],
            "sex_code": ["1"],
            "year": ["2024"],
            "migrations": [100],
        }
    )

    clear_migration_table()
    create_migration_table()
    insert_migration_data(df)
    insert_migration_data(
        pd.DataFrame(
            {
                "from_lan_code": ["01"],
                "to_lan_code": ["03"],
                "sex_code": ["1"],
                "year": ["2024"],
                "migrations": [150],
            }
        )
    )

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*), SUM(migrations) FROM migration;")
            row_count, total_migrations = cursor.fetchone()

    assert row_count == 1
    assert total_migrations == 150
