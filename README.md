# SCB Data Pipeline

A Python data pipeline for retrieving regional population data from Statistics Sweden (SCB), transforming it, and storing it in PostgreSQL, plus an interactive Dash application for exploring that data geographically.

## Current pipeline

```text
SCB API
   │
   ▼
Python / pandas
   │
   ├── JSON-stat parsing
   ├── Data cleaning
   └── API request batching
   │
   ▼
PostgreSQL
   │
   ├── SQL queries
   │
   ▼
Analysis
   │
   ▼
Interactive Dash app
```

The current dataset contains monthly population data by Swedish municipality, age group and sex.

The project also includes municipality geometry data in GeoJSON format, which is used to connect population data to geographic locations.

## Technologies

* Python
* pandas
* Dash / dash-leaflet
* Plotly
* Shapely
* PostgreSQL
* psycopg
* pytest
* Docker
* GitHub Actions

## Project structure

```text
scb-project/
├── .github/
│   └── workflows/
│       └── ci.yml
├── data/
│   └── municipalities.geojson
├── src/
│   └── scb_data/
│       ├── database.py
│       ├── geography.py
│       ├── jsonstat.py
│       ├── population.py
│       ├── queries.py
│       ├── scb_api.py
│       └── visualisation.py
├── tests/
│   ├── conftest.py
│   ├── test_database.py
│   ├── test_geography.py
│   ├── test_jsonstat.py
│   ├── test_population.py
│   ├── test_queries.py
│   ├── test_scb_api.py
│   └── test_visualisation.py
├── app.py
├── Dockerfile
├── compose.yaml
├── pyproject.toml
├── requirements.txt
├── run_pipeline.py
└── playground.py
```

## Data source

The population data is retrieved from Statistics Sweden (SCB) using the PxWeb API.

The current pipeline uses SCB's table:

**Population per month by region, age and sex**

The data covers Swedish municipalities and monthly observations.

Municipality geometry is stored separately as GeoJSON and is used to connect the population data to geographic locations through municipality codes.

## Interactive application

`app.py` is a Dash application (built on `dash-leaflet`) for exploring the population data geographically. The whole app fits a single viewport with no page scrolling: a control bar (title, level selector, year slider/play button) on top, the map on the left, and the population stats on the right. The map itself has no street-tile basemap - just municipality or county borders on a plain background, restricted to roughly Sweden's bounding box - so the focus stays on geography relevant to the data rather than roads or place names.

* A selection point stays fixed at the center of the screen; the user pans and zooms the map underneath it to choose a location.
* A radius slider draws a circle (in real kilometers, not screen pixels) around that point.
* Municipalities within the radius are listed, nearest first, using each municipality's representative point, with a fallback to an exact point-in-polygon check so the municipality actually containing the selection point is never missed. The same areas are also highlighted directly on the map: a saturated blue for areas within the radius, amber for the one the pin is actually inside of.
* A level selector switches between municipality and county: at county level, the map shows dissolved county outlines (municipality borders merged with Shapely) and the same radius search is grouped up by county, using the whole county's population (not just the part inside the circle).
* A population pyramid (male/female by age group) is shown for the combined population of the selected municipalities or counties.
* A year slider - with play/pause - moves through every year of data available (2000-2024), animating the pyramid over time.

Run it locally with:

```bash
python app.py
```

`src/scb_data/visualisation.py` also includes a Plotly choropleth map (`create_population_map`) showing population by municipality on a colour scale; it is tested independently and not currently wired into `app.py`.

## Running locally

### 1. Start PostgreSQL

The project includes a Docker Compose configuration for the database:

```bash
docker compose up -d
```

This starts a PostgreSQL instance with:

```text
Database: scb
User:     scb
Password: development
Host:     localhost
Port:     5432
```

### 2. Install the Python package

Create and activate a virtual environment, then install the project:

```bash
pip install -e .
```

Install the dependencies if necessary:

```bash
pip install -r requirements.txt
```

### 3. Run the pipeline

```bash
python run_pipeline.py
```

This retrieves the configured SCB population data, transforms it, and loads it into PostgreSQL.

### 4. Run the interactive app

```bash
python app.py
```

See [Interactive application](#interactive-application) above.

### 5. Run the tests

```bash
pytest
```

The tests include unit tests for the data-processing, geography, and visualization modules, as well as database integration tests.

The database tests use a separate PostgreSQL database named `scb_test`.

## Continuous integration

GitHub Actions automatically:

1. Checks out the repository.
2. Starts a PostgreSQL service.
3. Builds the Docker image.
4. Runs the test suite inside the Docker container.

The workflow is defined in:

```text
.github/workflows/ci.yml
```

## Status

The project currently provides:

* SCB API integration
* JSON-stat to pandas conversion
* API request batching
* Data cleaning
* PostgreSQL storage
* SQL-based population queries
* Municipality GeoJSON data
* An interactive, borders-only map (no street tiles, restricted to Sweden) with a fixed-center selection point and radius circle
* Radius-based municipality lookup (representative-point distance, with an exact point-in-polygon fallback), highlighted directly on the map as well as listed
* A municipality/county level selector, grouping the radius search up to whole counties
* A population pyramid (male/female by age group) for the selected area
* A year slider with play/pause, animating through 2000-2024
* A standalone Plotly choropleth map (tested, not wired into the interactive app)
* Unit and database integration tests
* Docker-based test execution
* GitHub Actions CI

## Roadmap

No further items are currently planned.
