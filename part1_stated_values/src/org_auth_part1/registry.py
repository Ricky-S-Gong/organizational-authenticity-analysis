"""Validate the reviewed page-candidate registry used for CDX collection."""

import argparse
import csv
from pathlib import Path

from org_auth_part1.models import PageCandidate
from org_auth_part1.targets import load_companies

DEFAULT_CANDIDATES = Path("part1_stated_values/config/page_candidates.csv")
DEFAULT_COMPANIES = Path("part1_stated_values/config/companies.csv")


def load_candidates(path: Path) -> list[PageCandidate]:
    with path.open(newline="", encoding="utf-8") as file:
        candidates = [PageCandidate.model_validate(row) for row in csv.DictReader(file)]
    return candidates


def validate_registry(
    candidates: list[PageCandidate], companies_path: Path = DEFAULT_COMPANIES
) -> dict[str, int]:
    companies = load_companies(companies_path)
    required_tickers = {company.ticker for company in companies}
    represented_tickers = {candidate.ticker for candidate in candidates}

    unknown = represented_tickers - required_tickers
    missing = required_tickers - represented_tickers
    if unknown:
        raise ValueError(f"unknown tickers in page registry: {sorted(unknown)}")
    if missing:
        raise ValueError(f"missing tickers in page registry: {sorted(missing)}")

    eligible = [candidate for candidate in candidates if candidate.eligibility_status == "eligible"]
    if not eligible:
        raise ValueError("page registry must contain eligible candidates")
    return {
        "companies": len(represented_tickers),
        "candidates": len(candidates),
        "eligible_candidates": len(eligible),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--companies", type=Path, default=DEFAULT_COMPANIES)
    args = parser.parse_args()

    summary = validate_registry(load_candidates(args.candidates), args.companies)
    print(
        f"Validated {summary['candidates']} candidates for "
        f"{summary['companies']} companies ({summary['eligible_candidates']} eligible)"
    )


if __name__ == "__main__":
    main()
