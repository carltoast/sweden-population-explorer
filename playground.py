"""Scratch file for ad hoc checks; not part of the pipeline."""

import json

from scb_data.queries import get_population_by_region
from scb_data.visualisation import create_population_map

with open("data/municipalities.geojson", encoding="utf-8") as f:
    geojson = json.load(f)

data = get_population_by_region("2024M12")

data = data.rename(
    columns={
        "region_code": "municipality_code",
        "region": "municipality_name",
    }
)

fig = create_population_map(data, geojson)
fig.write_html("test_map.html", auto_open=True)
