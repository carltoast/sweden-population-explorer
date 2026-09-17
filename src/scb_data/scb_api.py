"""Client for the SCB (Statistics Sweden) PxWeb API."""

import pandas as pd
import requests

from scb_data.jsonstat import jsonstat_to_dataframe

API_URL = "https://statistikdatabasen.scb.se/api/v2/tables/TAB5444/data"
TABLE_URL = "https://statistikdatabasen.scb.se/api/v2/tables/TAB5444"


def get_regions() -> list[dict]:
    """Fetch the list of Swedish municipalities from the SCB API.

    Returns:
        One dict per 4-digit municipality region code, each with "code"
        (the region code) and "name" (its human-readable label). Broader
        region groupings (e.g. national/county totals) are excluded by
        filtering to 4-character codes.
    """
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


def get_population_data(
    regions: list[str],
    ages: list[str],
    sexes: list[str],
    months: list[str],
) -> dict:
    """Fetch one batch of population data from the SCB API.

    Args:
        regions: Municipality region codes to request.
        ages: Age group codes to request.
        sexes: Sex codes to request ("1" male, "2" female).
        months: Month codes to request, in SCB's "YYYYMmm" format
            (e.g. "2024M12").

    Returns:
        The raw JSON-stat response payload.
    """
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


def batch_values(values: list[str], batch_size: int) -> list[list[str]]:
    """Split a list into consecutive chunks of at most batch_size items.

    Args:
        values: Values to split.
        batch_size: Maximum number of items per chunk.

    Returns:
        The values split into consecutive chunks, in original order.
    """
    return [
        values[i:i + batch_size]
        for i in range(0, len(values), batch_size)
    ]


def get_population_data_batched(
    regions: list[str],
    ages: list[str],
    sexes: list[str],
    months: list[str],
    region_batch_size: int = 50,
    month_batch_size: int = 10,
) -> pd.DataFrame:
    """Fetch population data for many regions/months, batched, as one frame.

    The SCB API limits how many region/month values a single request can
    carry, so regions and months are each split into chunks and fetched
    as separate requests, then concatenated into one DataFrame.

    Args:
        regions: Municipality region codes to request.
        ages: Age group codes to request.
        sexes: Sex codes to request ("1" male, "2" female).
        months: Month codes to request, in SCB's "YYYYMmm" format.
        region_batch_size: Maximum number of regions per request.
        month_batch_size: Maximum number of months per request.

    Returns:
        The combined JSON-stat results from every batch, converted to a
        DataFrame via jsonstat_to_dataframe.
    """
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
