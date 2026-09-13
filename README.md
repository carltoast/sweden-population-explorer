# SCB Data Pipeline

A Python data pipeline for retrieving regional population data from Statistics Sweden (SCB), transforming it, and storing it in PostgreSQL for analysis and visualization.

The project currently focuses on building a reliable data pipeline and exploring how the available SCB data can be used in a small analytical application.

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
Plotly visualization
```

The current dataset contains monthly population data by Swedish municipality, age group and sex.

The project also includes municipality geometry data in GeoJSON format, which is used to create geographic visualizations.

## Technologies

* Python
* pandas
* Plotly
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
│       ├── jsonstat.py
│       ├── population.py
│       ├── queries.py
│       ├── scb_api.py
│       └── visualisation.py
├── tests/
│   ├── conftest.py
│   ├── test_database.py
│   ├── test_jsonstat.py
│   ├── test_population.py
│   ├── test_queries.py
│   ├── test_scb_api.py
│   └── test_visualisation.py
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

Municipality geometry is stored separately as GeoJSON and is used to connect the population data to geographic visualizations through municipality codes.

## Visualization

The project currently includes a Plotly-based choropleth map showing population by Swedish municipality.

The visualization:

* Uses municipality codes to connect population data with geographic features.
* Displays population using a continuous colour scale.
* Shows municipality boundaries.
* Supports municipality names and population values on hover.
* Handles both Polygon and MultiPolygon municipality geometries.

The visualization is implemented in:

```text
src/scb_data/visualisation.py
```

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

### 4. Run the tests

```bash
pytest
```

The tests include unit tests for the data-processing and visualization modules as well as database integration tests.

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
* Plotly-based population visualization
* Unit and database integration tests
* Docker-based test execution
* GitHub Actions CI

The next stage is to develop the visualization into an interactive analytical application, allowing users to explore population data for individual municipalities and over time.
