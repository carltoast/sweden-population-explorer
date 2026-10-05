"""Tests for scb_data.migration."""

from unittest.mock import patch

import pandas as pd

from scb_data.migration import clean_migration_data, load_migration_data


def test_clean_migration_data():
    input_df = pd.DataFrame(
        {
            "InflyttningsL_code": ["01", "03"],
            "InflyttningsL": ["Stockholm county (to)", "Uppsala county (to)"],
            "UtflyttningsL_code": ["03", "01"],
            "UtflyttningsL": [
                "Uppsala county (from)", "Stockholm county (from)",
            ],
            "Kon_code": ["1", "2"],
            "Kon": ["men", "women"],
            "ContentsCode_code": ["000000OW", "000000OW"],
            "ContentsCode": ["Number", "Number"],
            "Tid_code": ["2024", "2024"],
            "Tid": ["2024", "2024"],
            "value": [3517, 3664],
        }
    )
    result = clean_migration_data(input_df)

    expected = pd.DataFrame(
        {
            "to_lan_code": ["01", "03"],
            "from_lan_code": ["03", "01"],
            "sex_code": ["1", "2"],
            "year": ["2024", "2024"],
            "migrations": [3517, 3664],
        }
    )

    pd.testing.assert_frame_equal(result, expected)


def test_load_migration_data():
    raw_data = pd.DataFrame(
        {
            "InflyttningsL_code": ["01"],
            "InflyttningsL": ["Stockholm county (to)"],
            "UtflyttningsL_code": ["03"],
            "UtflyttningsL": ["Uppsala county (from)"],
            "Kon_code": ["1"],
            "Kon": ["men"],
            "ContentsCode_code": ["000000OW"],
            "ContentsCode": ["Number"],
            "Tid_code": ["2024"],
            "Tid": ["2024"],
            "value": [3517],
        }
    )

    with (
        patch(
            "scb_data.migration.get_migration_data",
            return_value=raw_data,
        ) as mock_get_data,
        patch(
            "scb_data.migration.create_migration_table",
        ) as mock_create_table,
        patch(
            "scb_data.migration.insert_migration_data",
        ) as mock_insert,
    ):
        result = load_migration_data(years=["2024"])

    mock_get_data.assert_called_once_with(years=["2024"])

    mock_create_table.assert_called_once()
    mock_insert.assert_called_once()

    pd.testing.assert_frame_equal(result, mock_insert.call_args.args[0])
