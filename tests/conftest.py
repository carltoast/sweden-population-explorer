"""Shared pytest fixtures: point every test at a clean scb_test database."""

import pytest

from scb_data.database import clear_population_table, create_population_table


@pytest.fixture(autouse=True)
def test_database(monkeypatch):
    """Redirect the population table to scb_test and empty it.

    Runs automatically before every test: points POSTGRES_DB at the
    scb_test database, creates the population table if needed, and
    truncates it so each test starts from a known-empty state.
    """
    monkeypatch.setenv("POSTGRES_DB", "scb_test")
    create_population_table()
    clear_population_table()
