from __future__ import annotations

import pandas as pd
from org_auth_part3.constants import REQUIRED_INDEX_COLUMNS, TAXONOMY_VERSION
from org_auth_part3.validate import validate_outputs


def test_validate_outputs_passes_for_minimal_valid_panel(tmp_path) -> None:
    rows = []
    for idx in range(450):
        rows.append(
            {
                **{column: "" for column in REQUIRED_INDEX_COLUMNS},
                "ticker": f"T{idx:03d}",
                "year": 2016 + idx % 9,
                "score_status": "scored",
                "authenticity_index": 50,
                "cosine_alignment": 50,
                "l1_alignment": 50,
                "jaccard_theme_overlap": 50,
                "semantic_text_similarity": 75,
                "semantic_similarity_status": "computed",
                "semantic_similarity_gap_reason": "",
                "semantic_embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
                "sector_percentile": 0.5,
                "sector_z_score": 0,
                "part1_clean_text_sha256": "a",
                "part2_clean_text_sha256": "b",
                "taxonomy_version": TAXONOMY_VERSION,
            }
        )
    path = tmp_path / "index.csv"
    pd.DataFrame(rows).to_csv(path, index=False)

    audit = validate_outputs(path)

    assert audit["checks"]["expected_row_count"]
    assert audit["checks"]["required_columns_present"]
    assert audit["checks"]["scored_rows_have_scores"]
    assert audit["checks"]["scored_rows_traceable"]
