import os
import pytest

from scb_data.database import (
    create_population_table,
    clear_population_table
)

@pytest.fixture(autouse=True)
def test_database(monkeypatch):
    monkeypatch.setenv("POSTGRES_DB", "scb_test")
    create_population_table()
    clear_population_table()