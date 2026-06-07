"""Company and company-year target grid utilities for Part 2."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from org_auth_part2.models import Company, CompanyYear

PART2_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = PART2_ROOT.parent

DEFAULT_COMPANIES = REPO_ROOT / "part1_stated_values/config/companies.csv"
DEFAULT_OUTPUT = PART2_ROOT / "config/company_year_targets.csv"
TARGET_YEARS = tuple(range(2016, 2025))


def load_companies(path: Path = DEFAULT_COMPANIES) -> list[Company]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    companies: list[Company] = []
    for row in rows:
        ticker = row["ticker"].strip()
        if not ticker:
            continue
        companies.append(
            Company(
                ticker=ticker,
                company_name=row["company_name"].strip(),
                sector=row["sector"].strip(),
                primary_domain=row.get("primary_domain", "").strip(),
                known_historical_domains=row.get("known_historical_domains", "").strip(),
            )
        )
    return companies


def build_targets(
    companies: list[Company],
    years: tuple[int, ...] = TARGET_YEARS,
) -> list[CompanyYear]:
    return [
        CompanyYear(
            ticker=company.ticker,
            company_name=company.company_name,
            sector=company.sector,
            year=year,
        )
        for company in companies
        for year in years
    ]


def write_targets(targets: list[CompanyYear], path: Path = DEFAULT_OUTPUT) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["ticker", "company_name", "sector", "year"])
        writer.writeheader()
        for target in targets:
            writer.writerow(
                {
                    "ticker": target.ticker,
                    "company_name": target.company_name,
                    "sector": target.sector,
                    "year": target.year,
                }
            )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build the Part 2 50-company by 2016-2024 grid.")
    parser.add_argument("--companies", type=Path, default=DEFAULT_COMPANIES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    write_targets(build_targets(load_companies(args.companies)), args.output)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
