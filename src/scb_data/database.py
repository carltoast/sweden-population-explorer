"""Postgres connection handling and raw SQL for the population table."""

import os

import pandas as pd
import psycopg


def get_connection() -> psycopg.Connection:
    """Open a new connection to the population Postgres database.

    Connection parameters are read from the POSTGRES_HOST/PORT/DB/USER/
    PASSWORD environment variables, defaulting to the local Docker
    Compose values.

    Returns:
        An open psycopg connection.
    """
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "scb"),
        user=os.getenv("POSTGRES_USER", "scb"),
        password=os.getenv("POSTGRES_PASSWORD", "development"),
    )


def create_population_table() -> None:
    """Create the population table if it doesn't already exist.

    The primary key is (region_code, age_code, sex_code, month), one row
    per region/age group/sex/month combination.
    """
    query = """
        CREATE TABLE IF NOT EXISTS population (
            region_code VARCHAR(4) NOT NULL,
            region TEXT NOT NULL,
            age_code TEXT NOT NULL,
            age_group TEXT NOT NULL,
            sex_code TEXT NOT NULL,
            sex TEXT NOT NULL,
            month CHAR(7) NOT NULL,
            population INTEGER NOT NULL,
            PRIMARY KEY (region_code, age_code, sex_code, month)
        );
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)

        connection.commit()


def insert_population_data(df: pd.DataFrame) -> None:
    """Upsert population rows into the population table.

    Args:
        df: Rows with region_code, region, age_code, age_group, sex_code,
            sex, month, and population columns (as produced by
            scb_data.population.clean_population_data). On a primary-key
            conflict (same region_code/age_code/sex_code/month), the
            existing row's region/age_group/sex/population are updated
            in place rather than duplicated.
    """
    query = """
        INSERT INTO population (
            region_code,
            region,
            age_code,
            age_group,
            sex_code,
            sex,
            month,
            population
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (region_code, age_code, sex_code, month)
        DO UPDATE SET
            region = EXCLUDED.region,
            age_group = EXCLUDED.age_group,
            sex = EXCLUDED.sex,
            population = EXCLUDED.population;
    """

    rows = df[
        [
            "region_code",
            "region",
            "age_code",
            "age_group",
            "sex_code",
            "sex",
            "month",
            "population",
        ]
    ].itertuples(index=False, name=None)

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.executemany(query, rows)

        connection.commit()


def clear_population_table() -> None:
    """Delete all rows from the population table."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE population;")

        connection.commit()
