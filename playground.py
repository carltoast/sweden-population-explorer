import pandas as pd

from scb_data.scb_api import get_population_data_batched
#from scb_data.jsonstat import jsonstat_to_dataframe
from scb_data.scb_api import get_regions
from scb_data.population import clean_population_data
from scb_data.database import create_population_table

create_population_table()

print("Population table created.")

regions = get_regions()
region_codes = [region["code"] for region in regions]

print(f"Number of regions: {len(regions)}")

ages = [
    "-9",
    "10-19",
    "20-29",
    "30-39",
    "40-49",
    "50-59",
    "60-69",
    "70-79",
    "80-89",
    "90-99",
    "100+",
]

sexes = ["1", "2"]

months = [
    f"{year}M12"
    for year in range(2000, 2025)
]

data = get_population_data_batched(
    regions=region_codes,
    ages=ages,
    sexes=sexes,
    months=months,
    region_batch_size=50,
    month_batch_size=10,
)

data = clean_population_data(data)

print(data)
print()
print(f"Rows: {len(data)}")
print(f"Columns: {list(data.columns)}")
print()
print(data.head())

print()
print(data.shape)
print(data.head())
print(data.tail())

print()
print(data["region"].nunique())
print(data["month"].nunique())
print(data["age_group"].nunique())
print(data["sex"].nunique())

print(
    data.duplicated(
        subset=["region_code", "month", "age_code", "sex_code"]
    ).sum()
)
print(data.isna().sum())

