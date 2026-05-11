import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from ipam_gif_factory.interfaces.dashboard import run_dashboard

if __name__ == "__main__":
    run_dashboard()
