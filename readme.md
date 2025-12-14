# VRPTW Fulfilment Optimization

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![OR-Tools](https://img.shields.io/badge/OR--Tools-9.14+-green.svg)
![uv](https://img.shields.io/badge/uv-package%20manager-orange.svg)

A Vehicle Routing Problem with Time Windows (VRPTW) solver using OR-Tools, real-world geographic data from OpenStreetMap, and routing from OSRM.

## DSS Lecture Use Case: Würzburg Drinks Delivery

This fork is used for the **Decision Support Systems (DSS)** lecture. The scenario demonstrates route optimization for a drinks delivery service in Würzburg, Germany, delivering to bars and restaurants.

**Interactive Demo**: The marimo notebook in `apps/public/vrptw/vehicle_routing.py` can be run on [molab](https://marimo.io/cloud) - just upload the file and it will fetch all data from this repository automatically.

## Features

- **Real-world data**: Uses Overpass API to fetch pharmacy locations from OpenStreetMap
- **Accurate routing**: OSRM provides driving distances and durations with Bavaria coverage
- **Time windows**: Configurable service hours for depot and clients
- **Interactive visualization**: Matplotlib plots and Folium interactive maps
- **Scenario analysis**: Generate optimization results for multiple parameter combinations for research and analysis

## Setup

### Prerequisites

- Python 3.11+
- Docker (for OSRM)
- uv package manager

### Installation

1. Clone the repository:
```bash
git clone https://github.com/miTTimmiTTim/om_lecture_fulfilment.git
cd om_lecture_fulfilment
```

2. Install dependencies:
```bash
uv sync
```

3. Set up OSRM data (first time only):
```bash
mkdir -p osrm
cd osrm
wget http://download.geofabrik.de/europe/germany/bayern-latest.osm.pbf
cd ..
```

**Note**: The download is ~814MB and may take several minutes depending on your connection.

4. Start OSRM server with Bavaria data:
```bash
docker-compose up -d osrm
```

5. Test OSRM connection:
```bash
curl "http://127.0.0.1:9001/route/v1/driving/11.088860,49.517037;11.00385983,49.496891?overview=false"
```

## Usage

### Basic Usage

```bash
uv run python main.py
```

### Configuration

Edit parameters in `src/vrptw/config.py`:

- **Geography**: `center_lat`, `center_lon`, `radius_km`
- **Time windows**: `client_tw_start`, `client_tw_end`, `depot_tw_start`, `depot_tw_end`
- **Vehicles**: `vehicle_capacity`, `service_time_sec`, `vehicle_fixed_cost`
- **Solver**: `initial_vehicle_count`, `auto_increase_vehicles`, `time_limit_sec`

### Scenario Analysis

Generate optimization results for multiple parameter combinations:

```bash
# Generate all 1350 scenarios (15 radii × 9 time windows × 10 service times)
uv run python scenario_generator.py

# Test run with only 8 scenarios
uv run python scenario_generator.py --test-run

# Resume interrupted run
uv run python scenario_generator.py --resume

# Limit maximum radius
uv run python scenario_generator.py --max-radius 30
```

**Output**: Creates `scenario_data/` directory with:
- `pharmacies.parquet`: All pharmacy data with distance calculations (Polars format)
- `scenarios.csv`: Summary metrics for all scenarios
- `routes/scenario_*.json`: Detailed route data with OSRM geometries for offline visualization
- `completed.txt`: Checkpoint file for resumable execution

### Standard Usage Outputs

- Console summary with route details
- `vrp_routes.png`: Static visualization
- `vrp_routes.html`: Interactive map with dynamic colors

## Development

### Testing

```bash
uv run -m pytest
```

### Code Quality

```bash
# Format code
uvx ruff format .

# Check linting
uvx ruff check .

# Type checking
uvx mypy src/
```

## Architecture

```
/
├── main.py                    # Entry point with path setup
├── scenario_generator.py     # Scenario analysis generator
├── src/vrptw/                # Main package
│   ├── config.py             # Configuration dataclass
│   ├── solver.py             # OR-Tools VRPTW solver
│   ├── utils.py              # Result formatting utilities
│   ├── main.py               # Main execution logic
│   ├── scenario_config.py    # Scenario parameter generation
│   ├── scenario_storage.py   # Polars-based data storage
│   ├── data/                 # Data collection modules
│   │   ├── overpass.py       # OpenStreetMap pharmacy fetching
│   │   └── osrm.py           # OSRM distance matrices & routing
│   └── visualization/        # Plotting modules
│       ├── matplotlib_viz.py # Static plots
│       └── folium_viz.py     # Interactive maps
├── tests/                    # Test suite (29 tests)
├── scenario_data/            # Generated scenario analysis (gitignored)
├── docker-compose.yml        # OSRM container setup
└── osrm/                    # OSRM data directory (Bavaria)
```

## Key Features

- **Interactive visualization**: Folium maps with warehouse/pharmacy icons and CartoDB Light styling
- **Real-world routing**: OSRM integration provides accurate driving times and turn-by-turn directions
- **Automatic optimization**: OR-Tools determines optimal vehicle count based on constraints
- **Bavaria coverage**: Complete OSM data for accurate regional routing
- **Scenario analysis**: Generate 135 scenarios (15 radii × 9 time windows) with Polars-based data storage

## Algorithm Details

The solver uses OR-Tools with:
- **Vehicle count**: Automatically uses minimum vehicles needed (typically 9-12 for ~400 pharmacies)
- **Time windows**: 07:00-18:00 for clients, 05:00-19:00 for depot
- **Optimization**: Minimizes total travel time while respecting capacity and time constraints
- **Real routing**: OSRM provides accurate driving times and distances
- **Service time**: Configurable per pharmacy stop (1-10 minutes in scenario analysis)

## Performance

Example results for Erlangen/Nuremberg region (50km radius):
- **Pharmacies found**: ~437 locations
- **Vehicles used**: 50 (optimized automatically)
- **Total distance**: ~2,650 km
- **Total time**: ~115 hours
- **Average stops**: 8.7 per vehicle
- **Execution time**: ~107 seconds

## Scenario Analysis

The scenario generator creates comprehensive datasets for research and analysis:

**Parameter Space**:
- **Search radii**: 5-75km in 5km steps (15 values)
- **Time windows**: Always start 07:00, vary length 2-10 hours (9 values)
- **Service times**: 1-10 minutes per stop in 1-minute steps (10 values)
- **Total combinations**: 1350 scenarios

**Data Storage** (Polars-based for performance):
- **pharmacies.parquet**: All pharmacy locations with distance calculations
- **scenarios.csv**: Summary metrics (vehicles used, distances, execution times)
- **routes/scenario_*.json**: Route geometries for offline visualization
- **completed.txt**: Checkpoint system for resumable execution

**Use Cases**:
- Parameter sensitivity analysis
- Time window impact studies
- Service time optimization research
- Geographic coverage optimization
- Academic research and presentations
- Visualization without OSRM dependency