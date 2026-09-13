import pandas as pd

from scb_data.database import get_connection


def get_population_by_region(month):
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

def get_population_change(month):
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