"""Clean SCB county-to-county migration data and load it into Postgres."""

import pandas as pd

from scb_data.database import create_migration_table, insert_migration_data
from scb_data.scb_api import get_migration_data


def clean_migration_data(df: pd.DataFrame) -> pd.DataFrame:
    """Rename/drop raw SCB jsonstat columns into the migration DB schema.

    Args:
        df: Raw data as returned by scb_data.scb_api.get_migration_data,
            with SCB's own dimension column names ("InflyttningsL",
            "UtflyttningsL", "Kon", "Tid", etc).

    Returns:
        The same rows with columns renamed to the migration table's
        schema (from_lan_code, to_lan_code, sex_code, year,
        migrations); the label columns (county/sex names - the app
        already has its own name tables, see geography.COUNTY_NAMES)
        and ContentsCode (this table has only one measure) are
        dropped since the pipeline doesn't need them.
    """
    df = df.drop(
        columns=[
            "InflyttningsL",
            "UtflyttningsL",
            "Kon",
            "ContentsCode_code",
            "ContentsCode",
            "Tid_code",
        ]
    )

    df = df.rename(
        columns={
            "UtflyttningsL_code": "from_lan_code",
            "InflyttningsL_code": "to_lan_code",
            "Kon_code": "sex_code",
            "Tid": "year",
            "value": "migrations",
        }
    )

    return df


def load_migration_data(years: list[str]) -> pd.DataFrame:
    """Fetch county-to-county migration data from the SCB API and store it.

    Args:
        years: Calendar years to load, as 4-digit strings (e.g.
            "2024").

    Returns:
        The cleaned data that was inserted into the migration table.
    """
    data = get_migration_data(years=years)
    data = clean_migration_data(data)

    create_migration_table()
    insert_migration_data(data)

    return data
