# Change Validation

## Decision

Adjacent-year change detection is complete for all 450 company-year rows.

## Evidence

- `outputs/change_events.csv` contains one row per company-year.
- Usable adjacent-year pairs receive deterministic similarity scores and change classes.
- Comparisons involving missing or unusable text retain null change claims.
- Gap rows are not interpreted as evidence of stability or change.

## Rule

The pipeline compares only adjacent calendar years within the same ticker. It never substitutes
neighboring years for missing target-year captures.
