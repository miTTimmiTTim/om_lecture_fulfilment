# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Vehicle Routing Problem with Time Windows (VRPTW) solver for pharmaceutical delivery optimization hosted at https://github.com/NikoStein/om_lecture_fulfilment. The system uses real-world data from OpenStreetMap (via Overpass API) and routing from OSRM (Open Source Routing Machine) to optimize delivery routes in Bavaria, Germany.

**Repository Status**: Private repository for academic/lecture use.

## Architecture & Structure

### Modern Python Project Layout
```
/
├── main.py                    # Entry point with path setup
├── scenario_generator.py     # Scenario analysis generator
├── src/vrptw/                # Main package (proper src layout)
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
├── tests/                    # pytest test suite (29 tests)
├── scenario_data/            # Generated scenario analysis (gitignored)
├── docker-compose.yml        # OSRM container setup
└── osrm/                    # OSRM data directory (Bavaria coverage)
```

### Package Management & Tools
- **uv**: Modern Python package manager (replaces pip/poetry)
- **ruff**: Linting and formatting (replaces black/flake8/isort)
- **pytest**: Test suite with mocking for API dependencies
- **OR-Tools**: Google's optimization library for VRPTW solving
- **Polars**: High-performance DataFrame library for scenario data storage
- **tqdm**: Progress bars for long-running scenario generation
- **Modern types**: Uses `list[dict]` instead of `List[Dict]`, `X | None` instead of `Optional[X]`

## Core Components

### Configuration System
All parameters centralized in `src/vrptw/config.py` as a dataclass:
- **Geography**: `center_lat`, `center_lon`, `radius_km` (Erlangen/Nuremberg region)
- **Time windows**: 07:00-18:00 clients, 05:00-19:00 depot
- **Vehicles**: 50 capacity, 600s service time, auto-scaling enabled
- **Solver**: 20s time limit, PATH_CHEAPEST_ARC + GUIDED_LOCAL_SEARCH

### Data Pipeline
1. **Overpass API**: Fetch ~397 pharmacies within 50km radius
2. **OSRM Matrix**: Calculate driving times/distances between all pairs
3. **Route Geometry**: Get turn-by-turn routing for visualization

### Solver Implementation
- **OR-Tools only**: Removed PyVRP, uses Google's constraint solver
- **Real-world optimization**: OSRM durations as travel time + service time
- **Automatic vehicle count**: Starts with upper bound (50), uses minimum needed (~9)
- **Time window constraints**: Hard constraints on service hours
- **Capacity constraints**: Unit demand per pharmacy, 50 pharmacy capacity per vehicle

## Required Services

### OSRM Setup (Bavaria Data)
OSRM runs in Docker with full Bavaria OSM data for comprehensive coverage:

```bash
# Start OSRM with docker-compose (recommended)
docker-compose up -d osrm

# Test OSRM connectivity
curl "http://127.0.0.1:9001/route/v1/driving/11.088860,49.517037;11.00385983,49.496891?overview=false"
```

The container uses:
- **Data**: `bayern-latest.osm.pbf` (814MB, full Bavaria coverage)
- **Algorithm**: MLD (Multi-Level Dijkstra) for fast routing
- **Port**: 9001 (mapped to container's 5000)
- **Max table size**: 20,000 for large distance matrices

## Common Operations

### Development Workflow
```bash
# Install dependencies
uv sync

# Run application
uv run python main.py

# Run tests
uv run -m pytest

# Code quality
uvx ruff check .        # Lint
uvx ruff format .       # Format  
uvx mypy src/          # Type check
```

### Scenario Analysis Workflow
```bash
# Generate all 135 scenarios (15 radii × 9 time windows)
uv run python scenario_generator.py

# Test run with 4 scenarios
uv run python scenario_generator.py --test-run

# Resume interrupted execution
uv run python scenario_generator.py --resume

# Limit maximum radius
uv run python scenario_generator.py --max-radius 30
```

**Output Structure**:
- `scenario_data/pharmacies.parquet`: All pharmacy data with distance calculations (Polars format)
- `scenario_data/scenarios.csv`: Summary metrics for all 135 scenarios
- `scenario_data/routes/scenario_*.json`: Detailed route data with OSRM geometries
- `scenario_data/completed.txt`: Checkpoint file for resumable execution
- `scenario_data/metadata.json`: Dataset description and parameters

### Expected Output
Example performance for Erlangen/Nuremberg region:
- **Input**: 437 pharmacies within 50km radius
- **Solution**: 50 vehicles, ~2,650km total distance, ~115 hours total time
- **Execution**: ~107 seconds total pipeline time
- **Files**: `vrp_routes.png` (static plot), `vrp_routes.html` (interactive map with CartoDB styling)

## Key Design Decisions

### Removed Legacy Components
- **No cache.py**: Removed API caching for cleaner architecture
- **No debugging features**: Removed snap points, haversine fallbacks, diagnostics CSV
- **No Jupyter examples**: Focused on production-ready command-line interface

### Modern Python Practices
- **src/ layout**: Proper package structure with `src/vrptw/`
- **Type hints**: Modern union syntax (`X | None`), built-in generics (`list[str]`)
- **Professional visualization**: CartoDB Light maps with warehouse/pharmacy icons and dynamic colors
- **Relative imports**: Proper `from ..module import` structure
- **Entry point**: Root `main.py` handles path setup for direct execution
- **Quality tooling**: uv package management, ruff linting/formatting, comprehensive test suite

### Scenario Analysis Features
- **Comprehensive parameter space**: 15 radii (5-75km) × 9 time windows (2-10h) × 10 service times (1-10min) = 1350 scenarios
- **Polars-based storage**: High-performance DataFrames for efficient data processing
- **Resumable execution**: Checkpoint system with `completed.txt` tracking
- **Offline visualization**: Pre-computed OSRM geometries stored for later use without OSRM dependency
- **Research-ready output**: CSV summaries, Parquet pharmacy data, JSON route details

### Algorithm Improvements
- **Centralized OSRM functions**: All routing logic in `data/osrm.py`
- **Efficient vehicle usage**: OR-Tools automatically minimizes vehicle count
- **Real-world constraints**: Time windows enforce business hours
- **Scalable geography**: Bavaria coverage supports larger regions

## Testing Strategy

The test suite (29 tests) covers:
- **Config validation**: Dataclass instantiation and parameters
- **API mocking**: Overpass and OSRM responses without external dependencies
- **Solver logic**: OR-Tools requirement checking and result containers
- **Scenario generation**: Parameter combinations and ID generation (13 tests)
- **Data storage**: Polars DataFrame operations and file I/O (11 tests)
- **Import structure**: Validates relative import paths work correctly

Run with: `uv run -m pytest` (should complete in ~0.8s)