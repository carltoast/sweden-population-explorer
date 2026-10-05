"""Tests for scb_data.scb_api."""

from unittest.mock import Mock, patch

from scb_data.scb_api import (
    batch_values,
    get_migration_data,
    get_population_data,
)


def test_get_population_data():
    fake_response = Mock()
    fake_response.json.return_value = {"test": "data"}

    with patch(
        "scb_data.scb_api.requests.get",
        return_value=fake_response,
    ) as mock_get:
        result = get_population_data(
            regions=["0180", "1480"],
            ages=["-9", "10-19"],
            sexes=["1", "2"],
            months=["2024M12"],
        )

    assert result == {"test": "data"}

    mock_get.assert_called_once_with(
        "https://statistikdatabasen.scb.se/api/v2/tables/TAB5444/data",
        params={
            "lang": "en",
            "valueCodes[ContentsCode]": "000003O5",
            "valueCodes[Region]": "0180,1480",
            "valueCodes[Alder]": "-9,10-19",
            "valueCodes[Kon]": "1,2",
            "valueCodes[Tid]": "2024M12",
            "codelist[Region]": "vs_RegionKommun07",
            "codelist[Alder]": "agg_Ålder10årJ",
            "outputValues[Alder]": "aggregated",
        },
    )


def test_get_migration_data():
    fake_jsonstat = {
        "id": ["InflyttningsL", "UtflyttningsL", "Kon", "ContentsCode", "Tid"],
        "size": [2, 2, 1, 1, 1],
        "dimension": {
            "InflyttningsL": {
                "category": {
                    "index": {"01": 0, "03": 1},
                    "label": {"01": "Stockholm", "03": "Uppsala"},
                }
            },
            "UtflyttningsL": {
                "category": {
                    "index": {"01": 0, "03": 1},
                    "label": {"01": "Stockholm", "03": "Uppsala"},
                }
            },
            "Kon": {
                "category": {
                    "index": {"1": 0},
                    "label": {"1": "men"},
                }
            },
            "ContentsCode": {
                "category": {
                    "index": {"000000OW": 0},
                    "label": {"000000OW": "Number"},
                }
            },
            "Tid": {
                "category": {
                    "index": {"2024": 0},
                    "label": {"2024": "2024"},
                }
            },
        },
        "value": [0, 100, 90, 0],
    }

    fake_response = Mock()
    fake_response.json.return_value = fake_jsonstat

    with patch(
        "scb_data.scb_api.requests.get",
        return_value=fake_response,
    ) as mock_get:
        result = get_migration_data(years=["2024"])

    mock_get.assert_called_once_with(
        "https://statistikdatabasen.scb.se/api/v2/tables/TAB4409/data",
        params={
            "lang": "en",
            "valueCodes[ContentsCode]": "000000OW",
            "valueCodes[InflyttningsL]": "*",
            "valueCodes[UtflyttningsL]": "*",
            "valueCodes[Kon]": "1,2",
            "valueCodes[Tid]": "2024",
        },
    )

    assert list(result["InflyttningsL_code"]) == ["01", "01", "03", "03"]
    assert list(result["UtflyttningsL_code"]) == ["01", "03", "01", "03"]
    assert list(result["value"]) == [0, 100, 90, 0]


def test_batch_values_even_batches():
    values = list(range(10))
    result = batch_values(values, batch_size=5)
    assert result == [
        [0, 1, 2, 3, 4],
        [5, 6, 7, 8, 9]
    ]


def test_batch_values_with_remainder():
    values = list(range(10))
    result = batch_values(values, batch_size=4)
    assert result == [
        [0, 1, 2, 3],
        [4, 5, 6, 7],
        [8, 9]
    ]
