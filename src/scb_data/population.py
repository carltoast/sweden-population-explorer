import pandas as pd
from scb_data.database import (
    create_population_table,
    insert_population_data
)
from scb_data.scb_api import get_population_data_batched

def clean_population_data(df):
    df = df.drop(
        columns=[
            "ContentsCode_code",
            "ContentsCode",
            "Tid_code",
        ]
    )

    df = df.rename(
        columns={
            "Region_code": "region_code",
            "Region": "region",
            "Alder_code": "age_code",
            "Alder": "age_group",
            "Kon_code": "sex_code",
            "Kon": "sex",
            "Tid": "month",
            "value": "population",
        }
    )

    return df

def load_population_data(regions, ages, sexes, months):
    data = get_population_data_batched(
        regions=regions,
        ages=ages,
        sexes=sexes,
        months=months,
    )

    data = clean_population_data(data)

    create_population_table()
    insert_population_data(data)
    
    return data