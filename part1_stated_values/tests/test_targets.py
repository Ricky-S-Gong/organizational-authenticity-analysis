import csv
from pathlib import Path

from org_auth_part1.targets import build_targets, load_companies, write_targets

ROOT = Path(__file__).resolve().parents[2]
COMPANIES = ROOT / "part1_stated_values/config/companies.csv"


def test_company_manifest_has_required_sample_shape() -> None:
    companies = load_companies(COMPANIES)

    assert len(companies) == 50
    assert len({company.ticker for company in companies}) == 50


def test_target_grid_has_all_450_company_years(tmp_path: Path) -> None:
    targets = build_targets(load_companies(COMPANIES))
    output = tmp_path / "targets.csv"
    write_targets(targets, output)

    with output.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    assert len(rows) == 450
    assert len({(row["ticker"], row["year"]) for row in rows}) == 450
    assert {row["observation_status"] for row in rows} == {"pending"}


def test_default_paths_are_relative_to_repository_working_directory() -> None:
    from org_auth_part1.targets import DEFAULT_COMPANIES, DEFAULT_OUTPUT

    assert not DEFAULT_COMPANIES.is_absolute()
    assert not DEFAULT_OUTPUT.is_absolute()
