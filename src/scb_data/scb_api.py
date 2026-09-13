import requests
import pandas as pd

from scb_data.jsonstat import jsonstat_to_dataframe 

API_URL = "https://statistikdatabasen.scb.se/api/v2/tables/TAB5444/data"
TABLE_URL = "https://statistikdatabasen.scb.se/api/v2/tables/TAB5444"


def get_regions():
    url = "https://statistikdatabasen.scb.se/api/v2/tables/TAB5444/metadata"

    response = requests.get(
        url,
        params={"lang": "en"},
    )
    response.raise_for_status()

    data = response.json()

    category = data["dimension"]["Region"]["category"]

    codes = [
        code
        for code, _ in sorted(
            category["index"].items(),
            key=lambda item: item[1],
        )
    ]

    return [
        {
            "code": code,
            "name": category["label"][code],
        }
        for code in codes
        if len(code) == 4
    ]


def get_population_data(regions, ages, sexes, months):
    url = "https://statistikdatabasen.scb.se/api/v2/tables/TAB5444/data"

    params = {
        "lang": "en",
        "valueCodes[ContentsCode]": "000003O5",
        "valueCodes[Region]": ",".join(regions),
        "valueCodes[Alder]": ",".join(ages),
        "valueCodes[Kon]": ",".join(sexes),
        "valueCodes[Tid]": ",".join(months),
        "codelist[Region]": "vs_RegionKommun07",
        "codelist[Alder]": "agg_Ålder10årJ",
        "outputValues[Alder]": "aggregated",
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    return response.json()

def batch_values(values, batch_size):
    return [
        values[i:i + batch_size]
        for i in range(0, len(values), batch_size)
    ]

def get_population_data_batched(
    regions,
    ages,
    sexes,
    months,
    region_batch_size=50,
    month_batch_size=10,
):
    region_batches = batch_values(regions, region_batch_size)
    month_batches = batch_values(months, month_batch_size)

    dataframes = []

    for region_batch in region_batches:
        for month_batch in month_batches:
            response = get_population_data(
                regions=region_batch,
                ages=ages,
                sexes=sexes,
                months=month_batch,
            )

            df = jsonstat_to_dataframe(response)
            dataframes.append(df)

    return pd.concat(dataframes, ignore_index=True)