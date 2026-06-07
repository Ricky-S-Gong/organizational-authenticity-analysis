from pathlib import Path

from org_auth_part2.targets import (
    DEFAULT_COMPANIES,
    TARGET_YEARS,
    build_targets,
    load_companies,
    write_targets,
)


def test_build_targets_from_fixed_company_manifest() -> None:
    companies = load_companies(DEFAULT_COMPANIES)
    targets = build_targets(companies)
    assert len(companies) == 50
    assert len(targets) == 450
    assert sorted({target.year for target in targets}) == list(TARGET_YEARS)
    assert targets[0].ticker == "MSFT"


def test_write_targets(tmp_path: Path) -> None:
    companies = load_companies(DEFAULT_COMPANIES)[:1]
    output = tmp_path / "targets.csv"
    write_targets(build_targets(companies), output)
    text = output.read_text(encoding="utf-8")
    assert "ticker,company_name,sector,year" in text
    assert "MSFT,Microsoft,Technology,2016" in text
