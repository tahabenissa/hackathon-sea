"""Download NOAA NDBC historical standard-meteorological files (Phase 1).

Usage:  python ml/download_ndbc.py <station> <year> [<year> ...]
Example station IDs are listed on https://www.ndbc.noaa.gov/ (choose an
active cluster of nearby buoys; check that the years you want exist).
"""

import sys
from pathlib import Path

import httpx

URL = "https://www.ndbc.noaa.gov/data/historical/stdmet/{station}h{year}.txt.gz"
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"


def download(station: str, year: int) -> Path:
    out = RAW / f"{station}h{year}.txt.gz"
    if out.exists():
        print(f"skip {out.name} (already downloaded)")
        return out
    url = URL.format(station=station.lower(), year=year)
    resp = httpx.get(url, timeout=60, follow_redirects=True)
    resp.raise_for_status()
    RAW.mkdir(parents=True, exist_ok=True)
    out.write_bytes(resp.content)
    print(f"saved {out.name} ({len(resp.content) / 1024:.0f} KB)")
    return out


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    station, years = sys.argv[1], [int(y) for y in sys.argv[2:]]
    for year in years:
        try:
            download(station, year)
        except httpx.HTTPStatusError as exc:
            print(f"failed {station} {year}: HTTP {exc.response.status_code}")


if __name__ == "__main__":
    main()
