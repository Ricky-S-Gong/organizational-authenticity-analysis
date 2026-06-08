"""Shared constants for Part 3 alignment scoring."""

from __future__ import annotations

from pathlib import Path

PART3_ROOT = Path("part3_authenticity")
PART1_DATASET = Path("part1_stated_values/outputs/part1_company_year.csv")
PART2_DATASET = Path("part2_lived_values/outputs/part2_company_year_compact.csv")

OUTPUT_DIR = PART3_ROOT / "outputs"
DOCS_DIR = PART3_ROOT / "docs"

INDEX_OUTPUT = OUTPUT_DIR / "part3_authenticity_index.csv"
DISTRIBUTION_OUTPUT = OUTPUT_DIR / "distribution_summary.csv"
SECTOR_OUTPUT = OUTPUT_DIR / "sector_summary.csv"
YEAR_OUTPUT = OUTPUT_DIR / "year_summary.csv"
COMPANY_OUTPUT = OUTPUT_DIR / "company_summary.csv"
VALIDITY_OUTPUT = OUTPUT_DIR / "validity_case_audit.csv"
SENSITIVITY_OUTPUT = OUTPUT_DIR / "sensitivity_summary.csv"
SEMANTIC_OUTPUT = OUTPUT_DIR / "semantic_similarity.csv"
AUDIT_OUTPUT = OUTPUT_DIR / "requirement_audit.json"
FIGURES_DIR = OUTPUT_DIR / "figures"

TAXONOMY_VERSION = "1.0.0-keyword-baseline"
SEMANTIC_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
SEMANTIC_REPRESENTATIVE_TEXT_MAX_CHARS = 9000

THEME_LABELS: dict[str, str] = {
    "customers_and_service": "Customers and service",
    "employees_and_workplace": "Employees and workplace",
    "innovation_and_excellence": "Innovation and excellence",
    "integrity_and_ethics": "Integrity and ethics",
    "diversity_equity_and_inclusion": "Diversity, equity, and inclusion",
    "social_impact_and_community": "Social impact and community",
    "environment_and_sustainability": "Environment and sustainability",
    "health_safety_and_wellbeing": "Health, safety, and wellbeing",
    "shareholders_and_performance": "Shareholders and performance",
    "leadership_and_accountability": "Leadership and accountability",
    "collaboration_and_partnership": "Collaboration and partnership",
    "purpose_and_identity": "Purpose and identity",
}

THEME_IDS = tuple(THEME_LABELS)

REQUIRED_INDEX_COLUMNS = (
    "ticker",
    "company_name",
    "sector",
    "year",
    "part1_observation_status",
    "part1_gap_reason",
    "part2_collection_status",
    "part2_gap_reason",
    "score_status",
    "score_gap_reason",
    "authenticity_index",
    "cosine_alignment",
    "l1_alignment",
    "jaccard_theme_overlap",
    "semantic_text_similarity",
    "semantic_similarity_status",
    "semantic_similarity_gap_reason",
    "semantic_embedding_model",
    "sector_percentile",
    "sector_z_score",
    "stated_theme_total_matches",
    "disclosure_theme_total_matches",
    "stated_top_themes",
    "disclosure_top_themes",
    "theme_gap_summary",
    "part1_clean_text_sha256",
    "part2_clean_text_sha256",
    "part1_source_url",
    "part2_sec_archive_url",
    "taxonomy_version",
    "part2_action_evidence_rate",
    "part2_stakeholder_rate",
    "part2_word_count",
)
