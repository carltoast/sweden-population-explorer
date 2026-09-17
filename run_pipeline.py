"""Fetch population data for every municipality, 2000-2024, into Postgres."""

from scb_data.population import load_population_data
from scb_data.scb_api import get_regions

regions = get_regions()
region_codes = [region["code"] for region in regions]

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
    "2000M12",
    "2001M12",
    "2002M12",
    "2003M12",
    "2004M12",
    "2005M12",
    "2006M12",
    "2007M12",
    "2008M12",
    "2009M12",
    "2010M12",
    "2011M12",
    "2012M12",
    "2013M12",
    "2014M12",
    "2015M12",
    "2016M12",
    "2017M12",
    "2018M12",
    "2019M12",
    "2020M12",
    "2021M12",
    "2022M12",
    "2023M12",
    "2024M12",
]

data = load_population_data(
    regions=region_codes,
    ages=ages,
    sexes=sexes,
    months=months,
)

print(f"Loaded {len(data)} rows.")
