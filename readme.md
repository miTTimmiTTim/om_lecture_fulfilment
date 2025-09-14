# VRPTW Fulfilment Optimization

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![OR-Tools](https://img.shields.io/badge/OR--Tools-9.14+-green.svg)
![uv](https://img.shields.io/badge/uv-package%20manager-orange.svg)

A Vehicle Routing Problem with Time Windows (VRPTW) solver for pharmacy delivery optimization using OR-Tools, real-world geographic data from OpenStreetMap, and routing from OSRM.

## Features

- **Real-world data**: Uses Overpass API to fetch pharmacy locations from OpenStreetMap
- **Accurate routing**: OSRM provides driving distances and durations with Bavaria coverage
- **Time windows**: Configurable service hours for depot and clients
- **Interactive visualization**: Matplotlib plots and Folium interactive maps

## Setup

### Prerequisites

- Python 3.11+
- Docker (for OSRM)
- uv package manager

### Installation

1. Clone the repository:
```bash
git clone https://github.com/NikoStein/om_lecture_fulfilment.git
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

### Outputs

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
├── main.py               # Entry point with path setup
├── src/vrptw/           # Main package
│   ├── config.py        # Configuration dataclass
│   ├── solver.py        # OR-Tools VRPTW solver
│   ├── utils.py         # Result formatting utilities
│   ├── main.py          # Main execution logic
│   ├── data/            # Data collection modules
│   │   ├── overpass.py  # OpenStreetMap pharmacy fetching
│   │   └── osrm.py      # OSRM distance matrices & routing
│   └── visualization/   # Plotting modules
│       ├── matplotlib_viz.py  # Static plots
│       └── folium_viz.py      # Interactive maps
├── tests/               # Test suite
├── docker-compose.yml   # OSRM container setup
└── osrm/               # OSRM data directory (Bavaria)
```

## Key Features

- **Interactive visualization**: Folium maps with warehouse/pharmacy icons and CartoDB Light styling
- **Real-world routing**: OSRM integration provides accurate driving times and turn-by-turn directions
- **Automatic optimization**: OR-Tools determines optimal vehicle count based on constraints
- **Bavaria coverage**: Complete OSM data for accurate regional routing

## Algorithm Details

The solver uses OR-Tools with:
- **Vehicle count**: Automatically uses minimum vehicles needed (typically 9-12 for ~400 pharmacies)
- **Time windows**: 07:00-18:00 for clients, 05:00-19:00 for depot
- **Optimization**: Minimizes total travel time while respecting capacity and time constraints
- **Real routing**: OSRM provides accurate driving times and distances
- **Service time**: 10 minutes per pharmacy stop

## Performance

Example results for Erlangen/Nuremberg region (50km radius):
- **Pharmacies found**: ~437 locations
- **Vehicles used**: 50 (optimized automatically)
- **Total distance**: ~2,650 km
- **Total time**: ~115 hours
- **Average stops**: 8.7 per vehicle
- **Execution time**: ~107 seconds