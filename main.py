#!/usr/bin/env python3
"""Entry point for VRPTW solver with proper src/ path setup."""

import sys
from pathlib import Path

# Add src to Python path for direct execution
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from vrptw.main import main  # noqa: E402

if __name__ == "__main__":
    try:
        print("Starting VRPTW Solver...")
        print("=" * 50)

        result = main()

        if result.status == "OK":
            print("\n" + "=" * 50)
            print("✅ VRPTW solver completed successfully!")
            print(f"   • {result.vehicles_used} vehicles used")
            print(f"   • {result.total_distance_km:.1f}km total distance")
            print(f"   • {result.total_time_sec / 3600:.1f}h total time")
            print("\nCheck output files:")
            print("   • vrp_routes.png (static plot)")
            print("   • vrp_routes.html (interactive map)")

        else:
            print("\n" + "=" * 50)
            print(f"❌ VRPTW solver failed with status: {result.status}")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n🛑 Execution interrupted by user")
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure OSRM server is running: docker-compose up -d osrm")
        print("  2. Check internet connection for Overpass API")
        print("  3. Verify OR-Tools is installed: uv add ortools")
        sys.exit(1)
