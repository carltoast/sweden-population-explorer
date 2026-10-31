"""Shared pytest fixtures: point every test at a clean scb_test database."""

import psycopg
import pytest

from scb_data.database import (
    clear_migration_table,
    clear_population_table,
    create_migration_table,
    create_population_table,
    get_connection,
)


@pytest.fixture(scope="session", autouse=True)
def test_database_exists():
    """Create the scb_test database if it doesn't exist yet.

    Runs once before the suite. CI gets scb_test from its Postgres
    service container, but compose.yaml only creates scb, so without
    this a fresh clone fails every database-backed test. CREATE
    DATABASE can't run inside a transaction, hence autocommit, and
    Postgres has no IF NOT EXISTS for it, hence catching the
    duplicate instead of checking pg_database first (no race).
    """
    with get_connection(dbname="postgres") as connection:
        connection.autocommit = True

        try:
            connection.execute("CREATE DATABASE scb_test;")
        except psycopg.errors.DuplicateDatabase:
            pass


@pytest.fixture(autouse=True)
def test_database(test_database_exists, monkeypatch):
    """Redirect the population/migration tables to scb_test and empty them.

    Runs automatically before every test: points POSTGRES_DB at the
    scb_test database, creates both tables if needed, and truncates
    them so each test starts from a known-empty state.
    """
    monkeypatch.setenv("POSTGRES_DB", "scb_test")
    create_population_table()
    clear_population_table()
    create_migration_table()
    clear_migration_table()
