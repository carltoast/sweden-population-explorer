"""Clean SCB population data and load it into Postgres."""

import pandas as pd

from scb_data.database import (
    create_population_table,
    insert_population_data,
)
from scb_data.scb_api import get_population_data_batched


def clean_population_data(df: pd.DataFrame) -> pd.DataFrame:
    """Rename/drop raw SCB jsonstat columns into the population DB schema.

    Args:
        df: Raw data as returned by get_population_data_batched, with
            SCB's own dimension column names ("Region", "Alder", "Kon",
            "Tid", etc).

    Returns:
        The same rows with columns renamed to the population table's
        schema (region_code, region, age_code, age_group, sex_code, sex,
        month, population); the ContentsCode and Tid_code columns are
        dropped since they carry no information the pipeline needs.
    """
    df = df.drop(
        columns=[
            "ContentsCode_code",
            "ContentsCode",
            "Tid_code",
        ]
    )

    df = df.rename(
        columns={
            "Region_code": "region_code",
            "Region": "region",
            "Alder_code": "age_code",
            "Alder": "age_group",
            "Kon_code": "sex_code",
            "Kon": "sex",
            "Tid": "month",
            "value": "population",
        }
    )

    return df


def load_population_data(
    regions: list[str],
    ages: list[str],
    sexes: list[str],
    months: list[str],
) -> pd.DataFrame:
    """Fetch population data from the SCB API and store it in Postgres.

    Args:
        regions: Municipality region codes to load.
        ages: Age group codes to load.
        sexes: Sex codes to load ("1" male, "2" female).
        months: Month codes to load, in SCB's "YYYYMmm" format.

    Returns:
        The cleaned data that was inserted into the population table.
    """
    data = get_population_data_batched(
        regions=regions,
        ages=ages,
        sexes=sexes,
        months=months,
    )

    data = clean_population_data(data)

    create_population_table()
    insert_population_data(data)

    return data
