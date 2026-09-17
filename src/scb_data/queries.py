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


def get_population_by_region(month: str) -> pd.DataFrame:
    """Total population per region for a given month.

    Args:
        month: Month to query, in SCB's "YYYYMmm" format (e.g. "2024M12").

    Returns:
        Columns region_code, region, population (summed across age
        groups and sexes), sorted by population descending.
    """
    query = """
        SELECT
            region_code,
            region,
            SUM(population) AS population
        FROM population
        WHERE month = %s
        GROUP BY region_code, region
        ORDER BY population DESC;
    """

    with get_connection() as connection:
        return pd.read_sql_query(
            query,
            connection,
            params=(month,),
        )


def get_population_change(month: str) -> pd.DataFrame:
    """Total population per region per month, up to month, with deltas.

    Args:
        month: Latest month to include, in SCB's "YYYYMmm" format. All
            months up to and including this one are returned.

    Returns:
        Columns region_code, region, month, population (summed across
        age groups and sexes), and population_change (the difference
        from that region's previous month in the result, NaN for a
        region's first month), ordered by region then month.
    """
    query = """
        SELECT
            region_code,
            region,
            month,
            SUM(population) AS population,
            SUM(population) - LAG(SUM(population)) OVER (
                PARTITION BY region_code
                ORDER BY month
            ) AS population_change
        FROM population
        WHERE month <= %s
        GROUP BY region_code, region, month
        ORDER BY region_code, month;
    """

    with get_connection() as connection:
        return pd.read_sql_query(
            query,
            connection,
            params=(month,),
        )


def get_population_history(region_code: str, end_month: str) -> pd.DataFrame:
    """Total population for one region, month by month, up to end_month.

    Args:
        region_code: Municipality region code to query.
        end_month: Latest month to include, in SCB's "YYYYMmm" format.

    Returns:
        Columns month and population (summed across age groups and
        sexes), ordered chronologically.
    """
    query = """
        SELECT
            month,
            SUM(population) AS population
        FROM population
        WHERE region_code = %s
          AND month <= %s
        GROUP BY month
        ORDER BY month;
    """

    with get_connection() as connection:
        return pd.read_sql_query(
            query,
            connection,
            params=(region_code, end_month),
        )


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
