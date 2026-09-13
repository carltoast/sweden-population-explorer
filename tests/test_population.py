import pandas as pd
from unittest.mock import patch

from scb_data.population import (
    clean_population_data,
    load_population_data
)

def test_clean_population_data():
    input_df = pd.DataFrame(
        {
            "Region_code": ["0180", "1480"],
            "Region": ["Stockholm", "Göteborg"],
            "Alder_code": ["-9", "-9"],
            "Alder": ["0–9 years", "0–9 years"],
            "Kon_code": ["1", "2"],
            "Kon": ["men", "women"],
            "ContentsCode_code": ["000003O5", "000003O5"],
            "ContentsCode": ["Number", "Number"],
            "Tid_code": ["2024M12", "2024M12"],
            "Tid": ["2024M12", "2024M12"],
            "value": [53207, 50603],
        }
    )
    result = clean_population_data(input_df)

    expected = pd.DataFrame(
        {
            "region_code": ["0180", "1480"],
            "region": ["Stockholm", "Göteborg"],
            "age_code": ["-9", "-9"],
            "age_group": ["0–9 years", "0–9 years"],
            "sex_code": ["1", "2"],
            "sex": ["men", "women"],
            "month": ["2024M12", "2024M12"],
            "population": [53207, 50603],
        }
    )

    pd.testing.assert_frame_equal(result, expected)

def test_load_population_data():
    raw_data = pd.DataFrame(
        {
            "Region_code": ["0180"],
            "Region": ["Stockholm"],
            "Alder_code": ["-9"],
            "Alder": ["0–9 years"],
            "Kon_code": ["1"],
            "Kon": ["men"],
            "ContentsCode_code": ["000003O5"],
            "ContentsCode": ["Number"],
            "Tid_code": ["2024M12"],
            "Tid": ["2024M12"],
            "value": [53207],
        }
    )

    with (
        patch(
            "scb_data.population.get_population_data_batched",
            return_value=raw_data,
        ) as mock_get_data,
        patch(
            "scb_data.population.create_population_table",
        ) as mock_create_table,
        patch(
            "scb_data.population.insert_population_data",
        ) as mock_insert,
    ):
        result = load_population_data(
            regions=["0180"],
            ages=["-9"],
            sexes=["1"],
            months=["2024M12"],
        )

    mock_get_data.assert_called_once_with(
        regions=["0180"],
        ages=["-9"],
        sexes=["1"],
        months=["2024M12"],
    )

    mock_create_table.assert_called_once()
    mock_insert.assert_called_once()

    pd.testing.assert_frame_equal(result, mock_insert.call_args.args[0])