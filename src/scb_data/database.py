import os
import psycopg

def get_connection():
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "scb"),
        user=os.getenv("POSTGRES_USER", "scb"),
        password=os.getenv("POSTGRES_PASSWORD", "development"),
    )

def check_connection():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            result = cursor.fetchone()

    return result[0]

def create_population_table():
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

def insert_population_data(df):
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

def get_population_count():
    query = "SELECT COUNT(*) FROM population;"

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            result = cursor.fetchone()

    return result[0]

def clear_population_table():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE population;")

        connection.commit()