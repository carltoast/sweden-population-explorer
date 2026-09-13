from unittest.mock import Mock, patch

from scb_data.scb_api import (
    get_population_data,
    batch_values
)


def test_get_population_data():
    fake_response = Mock()
    fake_response.json.return_value = {"test": "data"}

    with patch("scb_data.scb_api.requests.get", return_value=fake_response) as mock_get:
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

