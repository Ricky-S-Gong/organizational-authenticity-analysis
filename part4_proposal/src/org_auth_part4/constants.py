"""Constants for the Part 4 proxy-genre sensitivity analysis."""

from __future__ import annotations

from pathlib import Path

PART4_ROOT = Path("part4_proposal")
OUTPUT_DIR = PART4_ROOT / "outputs"
FIGURE_DIR = OUTPUT_DIR / "figures"
DOCS_DIR = PART4_ROOT / "docs"

PART2_COMPACT = Path("part2_lived_values/outputs/part2_company_year_compact.csv")
PART2_FULL = Path("part2_lived_values/outputs/part2_company_year.csv")
PART3_INDEX = Path("part3_authenticity/outputs/part3_authenticity_index.csv")

DIAGNOSTICS_OUTPUT = OUTPUT_DIR / "part4_genre_diagnostics.csv"
SUMMARY_OUTPUT = OUTPUT_DIR / "genre_pressure_summary.csv"
CORRELATION_OUTPUT = OUTPUT_DIR / "genre_pressure_correlations.csv"
QUADRANT_OUTPUT = OUTPUT_DIR / "quadrant_genre_summary.csv"
CASE_AUDIT_OUTPUT = OUTPUT_DIR / "case_audit_targets.csv"
REGRESSION_OUTPUT = OUTPUT_DIR / "genre_pressure_regression.csv"
SECTION_OUTPUT = OUTPUT_DIR / "section_diagnostics.csv"
SECTION_SUMMARY_OUTPUT = OUTPUT_DIR / "section_summary.csv"
THEME_SEMANTIC_OUTPUT = OUTPUT_DIR / "theme_level_semantic_similarity.csv"
THEME_SEMANTIC_SUMMARY_OUTPUT = OUTPUT_DIR / "theme_level_semantic_summary.csv"
AUDIT_OUTPUT = OUTPUT_DIR / "requirement_audit.json"

SUMMARY_DOC = DOCS_DIR / "summary.md"
METHODOLOGY_DOC = DOCS_DIR / "methodology.md"
CODEBOOK_DOC = DOCS_DIR / "codebook.md"

SCATTER_FIGURE = FIGURE_DIR / "genre_pressure_vs_authenticity.png"
TERCILE_FIGURE = FIGURE_DIR / "genre_pressure_terciles.png"
QUADRANT_FIGURE = FIGURE_DIR / "quadrant_genre_pressure.png"
SECTION_FIGURE = FIGURE_DIR / "section_authenticity_contribution.png"
THEME_SEMANTIC_FIGURE = FIGURE_DIR / "theme_level_semantic_similarity.png"
SECTION_THEME_HEATMAP_FIGURE = FIGURE_DIR / "section_theme_heatmap.png"
THEME_SEMANTIC_GAP_FIGURE = FIGURE_DIR / "theme_semantic_gap_scatter.png"
SECTION_COMPOSITION_FIGURE = FIGURE_DIR / "section_theme_composition.png"

GENRE_DICTIONARIES: dict[str, tuple[str, ...]] = {
    "shareholder_mechanics": (
        "annual meeting",
        "special meeting",
        "proxy card",
        "record date",
        "beneficial owner",
        "street name",
        "broker non-vote",
        "quorum",
        "vote",
        "voting",
        "proposal",
        "proposals",
        "stockholder proposal",
        "shareholder proposal",
        "proxy statement",
    ),
    "governance_boilerplate": (
        "board",
        "board of directors",
        "committee",
        "audit committee",
        "compensation committee",
        "nominating",
        "corporate governance",
        "director",
        "directors",
        "independence",
        "independent director",
        "executive compensation",
        "compensation",
    ),
    "legal_procedural": (
        "pursuant",
        "in accordance",
        "regulation",
        "securities",
        "exchange act",
        "sec",
        "filing",
        "solicitation",
        "hereby",
        "applicable law",
        "rules and regulations",
        "safe harbor",
    ),
}

THEME_DICTIONARIES: dict[str, tuple[str, ...]] = {
    "customers_and_service": (
        "customer",
        "customers",
        "customer experience",
        "client",
        "clients",
        "consumer",
        "consumers",
        "patient",
        "patients",
        "service",
    ),
    "employees_and_workplace": (
        "employee",
        "employees",
        "our people",
        "workforce",
        "talent",
        "workplace",
        "professional development",
        "career development",
    ),
    "innovation_and_excellence": (
        "innovation",
        "innovative",
        "invent",
        "excellence",
        "quality",
        "continuous improvement",
        "best in class",
    ),
    "integrity_and_ethics": (
        "integrity",
        "ethical",
        "ethics",
        "honesty",
        "honest",
        "trust",
        "transparent",
        "transparency",
    ),
    "diversity_equity_and_inclusion": (
        "diversity",
        "diverse",
        "equity",
        "inclusion",
        "inclusive",
        "belonging",
        "equal opportunity",
    ),
    "social_impact_and_community": (
        "community",
        "communities",
        "social impact",
        "society",
        "philanthropy",
        "volunteer",
        "giving back",
    ),
    "environment_and_sustainability": (
        "sustainability",
        "sustainable",
        "environment",
        "environmental",
        "climate",
        "emissions",
        "renewable",
        "natural resources",
    ),
    "health_safety_and_wellbeing": (
        "health",
        "healthy",
        "safety",
        "safe",
        "wellbeing",
        "well-being",
        "security",
    ),
    "shareholders_and_performance": (
        "shareholder",
        "shareholders",
        "shareholder value",
        "financial performance",
        "profitable growth",
        "long-term value",
        "returns",
    ),
    "leadership_and_accountability": (
        "leadership",
        "leader",
        "leaders",
        "accountability",
        "accountable",
        "ownership",
        "responsibility",
        "responsible",
    ),
    "collaboration_and_partnership": (
        "collaboration",
        "collaborate",
        "teamwork",
        "partnership",
        "partnerships",
        "together",
    ),
    "purpose_and_identity": (
        "our purpose",
        "our mission",
        "our values",
        "core values",
        "who we are",
        "we exist to",
        "our vision",
    ),
}

SECTION_PATTERNS: dict[str, tuple[str, ...]] = {
    "meeting_voting": (
        "annual meeting",
        "information about the meeting",
        "voting",
        "vote",
        "proxy",
        "quorum",
        "record date",
    ),
    "governance_board": (
        "corporate governance",
        "board of directors",
        "director nominees",
        "board",
        "committees",
        "committee",
        "independence",
    ),
    "compensation": (
        "compensation discussion",
        "executive compensation",
        "compensation committee",
        "pay ratio",
        "incentive plan",
        "summary compensation",
    ),
    "shareholder_proposals": (
        "shareholder proposal",
        "stockholder proposal",
        "proposal",
        "proposals",
    ),
    "ownership": (
        "security ownership",
        "beneficial ownership",
        "principal shareholders",
        "stock ownership",
    ),
    "audit": (
        "audit committee",
        "independent registered public accounting firm",
        "ratification",
        "auditor",
    ),
    "human_capital_values": (
        "human capital",
        "employees",
        "diversity",
        "inclusion",
        "sustainability",
        "environment",
        "community",
        "culture",
        "values",
        "workforce",
    ),
    "legal_other": (
        "section 16",
        "securities exchange act",
        "other matters",
        "solicitation",
        "forward-looking",
    ),
}

REQUIRED_DIAGNOSTIC_COLUMNS = [
    "ticker",
    "company_name",
    "sector",
    "year",
    "genre_status",
    "score_status",
    "authenticity_index",
    "semantic_text_similarity",
    "keyword_minus_semantic",
    "shareholder_mechanics_count",
    "shareholder_mechanics_rate",
    "governance_boilerplate_count",
    "governance_boilerplate_rate",
    "legal_procedural_count",
    "legal_procedural_rate",
    "proxy_genre_pressure",
    "genre_pressure_tercile",
    "keyword_semantic_quadrant",
]

REQUIRED_SECTION_COLUMNS = [
    "ticker",
    "year",
    "section_family",
    "section_title",
    "section_word_count",
    "section_share_of_proxy",
    "section_genre_rate",
    "dominant_theme_id",
]

REQUIRED_THEME_SEMANTIC_COLUMNS = [
    "ticker",
    "year",
    "theme_id",
    "theme_semantic_status",
    "theme_semantic_similarity",
    "stated_excerpt_count",
    "disclosure_excerpt_count",
    "stated_theme_share",
    "disclosure_theme_share",
]
