# Part 1 Validation Report

## Result

All eight Part 1 phases have implemented code paths and corresponding automated tests. The current
live research run does **not** satisfy every Part 1 completion gate. This distinction is deliberate:
passing unit tests proves that the pipeline behaves as designed, while the phase audit checks
whether the required data collection, external LLM analysis, and human research validation are
actually complete.

Run the authoritative phase audit with:

```bash
uv run --no-sync part1-validate-phases
```

The machine-readable result is `outputs/phase_validation.json`.

## Phase Status

| Phase | Implementation and tests | Current research gate | Reason |
|---|---|---|---|
| 0. Environment and contract | Complete | Pass | 450 unique company-year targets, 50 companies, 9 years, and five sectors with 10 companies each |
| 1. Difficult pilot and rule lock | Complete | Open | Decision record exists, but human approval has not been recorded |
| 2. Candidate registry | Complete | Pass | Every required company has a reviewed candidate entry |
| 3. CDX collection and selection | Complete and resumable | Fail | 414 company-year rows remain `discovery_incomplete` after widespread Wayback failures |
| 4. Text extraction | Complete | Open | Selected captures were processed, but the manual review queue and human extraction-validation record remain open |
| 5. Change detection | Complete | Open | All 450 rows have change outputs, but a human-labelled agreement/sensitivity validation has not been recorded |
| 6. Theme and LLM analysis | Deterministic baseline complete | Fail | No external LLM run or LLM reproducibility metadata is available |
| 7. Reporting and deliverables | Structural outputs complete | Fail | Upstream research gates are incomplete, so the current sparse output is not a final substantive result |

## Automated Verification

The test suite contains phase-specific tests for target contracts, candidate registry validation,
CDX discovery, annual selection, retrieval, extraction, adjacent-year comparison, taxonomy,
reporting, final output audits, and phase gates.

```bash
uv sync --no-editable
uv run --no-sync pytest
uv run --no-sync ruff check .
uv run --no-sync part1-process
uv run --no-sync part1-validate-phases
```

The requirement audit checks the final 450-row contract, missingness, provenance, evidence, and
external completion gates. It is stored at `outputs/requirement_audit.json`.

## Human Review Needed

1. Review and approve the pilot decision record, then add `docs/pilot_approval.md`.
2. Resolve `data/review/manual_review_queue.csv`, document sampled precision/recall, and add
   `docs/extraction_validation.md`.
3. Label a stratified adjacent-year sample, document agreement and threshold sensitivity, and add
   `docs/change_validation.md`.
4. Run and validate the required LLM-assisted analysis with model, prompt, parameters, hashes,
   schema-validation results, token use, and cost metadata.

These files are completion evidence, not placeholders. They should be added only after the
corresponding review has genuinely occurred.

## External Recovery Procedure

When Wayback CDX is available again, rerun:

```bash
uv run --no-sync part1-discover
uv run --no-sync part1-select
uv run --no-sync part1-process
uv run --no-sync part1-validate-phases
```

Discovery and retrieval use cached successful results, so reruns resume rather than discard prior
work. A complete research result requires zero `discovery_incomplete` rows and all human and LLM
gates to be satisfied.
