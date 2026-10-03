"""Build the browser dashboard (results/dashboard.html) from results/*.csv and open it.

    python scripts/build_dashboard.py          # build and open in Chrome (or the default browser)
    python scripts/build_dashboard.py --no-open
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from traffic_signal.dashboard import build  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--results", type=Path, default=Path("results"))
    ap.add_argument("--no-open", action="store_true")
    args = ap.parse_args()
    if not (args.results / "timeseries.csv").exists():
        sys.exit(f"{args.results}/timeseries.csv not found - run scripts/run_experiments.py first")
    out = build(args.results).resolve()
    print(out)
    if args.no_open:
        return
    chrome = Path("/Applications/Google Chrome.app")
    if sys.platform == "darwin" and chrome.exists() and shutil.which("open"):
        subprocess.run(["open", "-a", str(chrome), str(out)], check=False)
    else:
        webbrowser.open(out.as_uri())


if __name__ == "__main__":
    main()
