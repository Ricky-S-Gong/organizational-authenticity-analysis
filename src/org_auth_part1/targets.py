"""Build and validate the complete 50-company by 9-year target grid."""

import argparse
import csv
from datetime import UTC, datetime
from pathlib import Path

from org_auth_part1.models import Company, CompanyYearTarget

DEFAULT_COMPANIES = Path("part1_stated_values/config/companies.csv")
DEFAULT_OUTPUT = Path("part1_stated_values/data/processed/target_company_years.csv")
TARGET_YEARS = range(2016, 2025)


def parse_domains(raw_value: str) -> list[str]:
    return [domain.strip() for domain in raw_value.split(";") if domain.strip()]


def load_companies(path: Path) -> list[Company]:
    with path.open(newline="", encoding="utf-8") as file:
        rows = csv.DictReader(file)
        companies = [
            Company(
                ticker=row["ticker"],
                company_name=row["company_name"],
                sector=row["sector"],
                primary_domain=row["primary_domain"],
                known_historical_domains=parse_domains(row["known_historical_domains"]),
            )
            for row in rows
        ]
    validate_company_manifest(companies)
    return companies


def validate_company_manifest(companies: list[Company]) -> None:
    if len(companies) != 50:
        raise ValueError(f"expected 50 companies, found {len(companies)}")

    tickers = [company.ticker for company in companies]
    if len(set(tickers)) != len(tickers):
        raise ValueError("company tickers must be unique")

    sector_counts: dict[str, int] = {}
    for company in companies:
        sector_counts[company.sector.value] = sector_counts.get(company.sector.value, 0) + 1
    if set(sector_counts.values()) != {10} or len(sector_counts) != 5:
        raise ValueError(f"expected five sectors with ten companies each, found {sector_counts}")


def build_targets(companies: list[Company]) -> list[CompanyYearTarget]:
    return [
        CompanyYearTarget(
            ticker=company.ticker,
            company_name=company.company_name,
            sector=company.sector,
            year=year,
            target_timestamp=datetime(year, 6, 30, 12, tzinfo=UTC),
        )
        for company in companies
        for year in TARGET_YEARS
    ]


def write_targets(targets: list[CompanyYearTarget], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "ticker",
        "company_name",
        "sector",
        "year",
        "target_timestamp",
        "observation_status",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for target in targets:
            writer.writerow(
                {
                    "ticker": target.ticker,
                    "company_name": target.company_name,
                    "sector": target.sector.value,
                    "year": target.year,
                    "target_timestamp": target.target_timestamp.isoformat(),
                    "observation_status": target.observation_status.value,
                }
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--companies", type=Path, default=DEFAULT_COMPANIES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    targets = build_targets(load_companies(args.companies))
    write_targets(targets, args.output)
    print(f"Wrote {len(targets)} targets to {args.output}")


if __name__ == "__main__":
    main()
