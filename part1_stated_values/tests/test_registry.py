from pathlib import Path

import pytest
from org_auth_part1.models import PageCandidate
from org_auth_part1.registry import load_candidates, validate_registry

ROOT = Path(__file__).resolve().parents[2]


def test_registry_represents_all_required_companies() -> None:
    candidates = load_candidates(ROOT / "part1_stated_values/config/page_candidates.csv")
    summary = validate_registry(candidates, ROOT / "part1_stated_values/config/companies.csv")

    assert summary["companies"] == 50
    assert summary["eligible_candidates"] >= 50


def test_registry_rejects_missing_company() -> None:
    candidates = [
        PageCandidate(
            ticker="MSFT",
            candidate_url="https://www.microsoft.com/about",
            page_type="about",
            discovery_method="manual_seed",
            eligibility_status="eligible",
            eligibility_reason="official corporate about page",
            reviewer="pipeline_seed",
        )
    ]

    with pytest.raises(ValueError, match="missing tickers"):
        validate_registry(candidates, ROOT / "part1_stated_values/config/companies.csv")
