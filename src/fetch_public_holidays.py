"""Fetch New Zealand public holidays from public-holidays.nz.

The API requires an API key. Store it in NZ_PUBLIC_HOLIDAYS_API_KEY, then run:

    python src/fetch_public_holidays.py --years 2023 2024 2025

The checked-in CSV under data/raw is a reproducible seed so Part 1 can run even
when no API key is available during review.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "raw" / "nz_public_holidays.csv"
API_BASE_URL = "https://api.public-holidays.nz/v1/year"
DOCS_URL = "https://www.public-holidays.nz/docs.asp"


def _pick(record: dict[str, Any], names: list[str]) -> Any:
    lower = {str(k).lower().replace("_", ""): v for k, v in record.items()}
    for name in names:
        key = name.lower().replace("_", "")
        if key in lower and lower[key] not in (None, ""):
            return lower[key]
    return None


def _holiday_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("holidays", "data", "result", "results", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            return [r for r in value if isinstance(r, dict)]
    return [payload] if payload else []


def fetch_year(year: int, api_key: str) -> pd.DataFrame:
    response = requests.get(
        API_BASE_URL,
        params={"apikey": api_key, "year": year},
        timeout=30,
    )
    response.raise_for_status()

    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError(f"API returned non-JSON response for {year}: {response.text[:200]}") from exc

    rows: list[dict[str, Any]] = []
    for record in _holiday_records(payload):
        name = _pick(record, ["holiday_name", "name", "holiday", "title"])
        observed = _pick(record, ["observed_date", "observedDate", "date", "holiday_date"])
        actual = _pick(record, ["actual_date", "actualDate", "date", "holiday_date"])
        holiday_date = pd.to_datetime(observed, errors="coerce", dayfirst=True)
        actual_date = pd.to_datetime(actual, errors="coerce", dayfirst=True)
        if pd.isna(holiday_date) or not name:
            continue
        rows.append(
            {
                "holiday_date": holiday_date.date().isoformat(),
                "holiday_name": str(name),
                "year": int(year),
                "scope": "National",
                "actual_date": "" if pd.isna(actual_date) else actual_date.date().isoformat(),
                "observed_date": holiday_date.date().isoformat(),
                "source_name": "public-holidays.nz API",
                "source_url": DOCS_URL,
                "notes": "Fetched from /v1/year endpoint",
            }
        )

    if not rows:
        raise RuntimeError(f"No normalisable holidays returned for {year}. Check API response shape.")
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", nargs="+", type=int, default=[2023, 2024, 2025])
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--api-key", default=os.getenv("NZ_PUBLIC_HOLIDAYS_API_KEY"))
    args = parser.parse_args()

    if not args.api_key:
        raise SystemExit(
            "Missing API key. Set NZ_PUBLIC_HOLIDAYS_API_KEY or keep using "
            f"the seeded file at {DEFAULT_OUTPUT}."
        )

    frames = [fetch_year(year, args.api_key) for year in args.years]
    holidays = pd.concat(frames, ignore_index=True)
    holidays = holidays.sort_values(["holiday_date", "holiday_name"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    holidays.to_csv(args.output, index=False)
    print(f"Wrote {len(holidays):,} holiday rows to {args.output}")


if __name__ == "__main__":
    main()
