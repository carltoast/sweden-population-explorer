"""Read-side SQL queries for the population table."""

import pandas as pd

from scb_data.database import get_connection

AGE_ORDER = [
    "-9",
    "10-19",
    "20-29",
    "30-39",
    "40-49",
    "50-59",
    "60-69",
    "70-79",
    "80-89",
    "90-99",
    "100+",
]


def get_available_months() -> list[str]:
    """List every month present in the population table.

    Returns:
        Month codes in SCB's "YYYYMmm" format (e.g. "2024M12"), sorted
        chronologically (which for this format is also alphabetical).
    """
    query = "SELECT DISTINCT month FROM population ORDER BY month;"

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            return [row[0] for row in cursor.fetchall()]


def get_population_pyramid(
    region_codes: list[str],
    month: str,
) -> pd.DataFrame:
    """Population by age group and sex, summed across region_codes.

    Args:
        region_codes: Municipality region codes to sum over.
        month: Month to query, in SCB's "YYYYMmm" format.

    Returns:
        Columns age_code, age_group, sex_code, sex, population, one row
        per age group/sex combination, ordered by age (youngest first,
        via AGE_ORDER - age_code sorts wrong alphabetically, e.g.
        "100+" < "20-29") then by sex_code.
    """
    query = """
        SELECT
            age_code,
            age_group,
            sex_code,
            sex,
            SUM(population) AS population
        FROM population
        WHERE region_code = ANY(%s)
          AND month = %s
        GROUP BY age_code, age_group, sex_code, sex;
    """

    with get_connection() as connection:
        result = pd.read_sql_query(
            query,
            connection,
            params=(region_codes, month),
        )

    result["age_code"] = pd.Categorical(
        result["age_code"],
        categories=AGE_ORDER,
        ordered=True,
    )

    return result.sort_values(["age_code", "sex_code"]).reset_index(drop=True)


def get_max_pyramid_value(region_codes: list[str]) -> float:
    """Largest single age/sex population total across every month.

    Used to fix the population pyramid's x-axis range for the whole
    play/pause animation up front, instead of get_population_pyramid's
    per-month result rescaling the axis on every frame.

    Args:
        region_codes: Municipality region codes to sum over.

    Returns:
        The largest month/age/sex population total (summed across
        region_codes) over all months, or 0.0 if none exists (e.g. an
        empty region_codes list).
    """
    query = """
        SELECT COALESCE(MAX(age_sex_population), 0) AS max_value
        FROM (
            SELECT SUM(population) AS age_sex_population
            FROM population
            WHERE region_code = ANY(%s)
            GROUP BY month, age_code, sex_code
        ) AS month_age_sex_totals;
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (region_codes,))
            return float(cursor.fetchone()[0])
