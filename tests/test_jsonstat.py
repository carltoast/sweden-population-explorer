"""Tests for scb_data.jsonstat."""

import pandas as pd

from scb_data.jsonstat import jsonstat_to_dataframe


def test_jsonstat_to_dataframe():
    data = {
        "id": ["Region", "Kon"],
        "size": [2, 2],
        "dimension": {
            "Region": {
                "category": {
                    "index": {
                        "0180": 0,
                        "1480": 1,
                    },
                    "label": {
                        "0180": "Stockholm",
                        "1480": "Göteborg",
                    },
                }
            },
            "Kon": {
                "category": {
                    "index": {
                        "1": 0,
                        "2": 1,
                    },
                    "label": {
                        "1": "men",
                        "2": "women",
                    },
                }
            },
        },
        "value": [53207, 50603, 32925, 31148],
    }

    result = jsonstat_to_dataframe(data)

    expected = pd.DataFrame(
        {
            "Region_code": ["0180", "0180", "1480", "1480"],
            "Region": ["Stockholm", "Stockholm", "Göteborg", "Göteborg"],
            "Kon_code": ["1", "2", "1", "2"],
            "Kon": ["men", "women", "men", "women"],
            "value": [53207, 50603, 32925, 31148],
        }
    )

    pd.testing.assert_frame_equal(result, expected)
