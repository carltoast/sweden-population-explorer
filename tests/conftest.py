"""Shared pytest fixtures: point every test at a clean scb_test database."""

import pytest

from scb_data.database import (
    clear_migration_table,
    clear_population_table,
    create_migration_table,
    create_population_table,
)


@pytest.fixture(autouse=True)
def test_database(monkeypatch):
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
