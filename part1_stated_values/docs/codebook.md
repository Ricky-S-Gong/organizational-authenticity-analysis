# Part 1 Data Codebook

Primary dataset: `outputs/part1_company_year.csv`

Supporting outputs:

- `outputs/change_events.csv`
- `outputs/theme_observations.csv`
- `outputs/llm_analysis/llm_snapshot_analysis.csv`
- `outputs/llm_analysis/llm_change_analysis.csv`
- `outputs/coverage_report.json`
- `outputs/requirement_audit.json`
- `outputs/phase_validation.json`

The primary dataset keeps all 450 required company-year rows. Usable rows contain extracted
substantive text and analysis fields; non-usable rows remain in the panel with explicit
`observation_status` and `gap_reason` values.

## Instruction-to-Output Map

The Part 1 instruction asks the LLM-based pipeline to analyze each snapshot for change, thematic
categories, and linguistic shifts. The submitted outputs expose those components in the following
places:

| Instruction item | Primary files and fields |
| --- | --- |
| Whether the page changed from the prior year | `outputs/part1_company_year.csv`: `changed_from_prior`, `change_score`, `change_magnitude`; `outputs/change_events.csv`: adjacent-year evidence; `outputs/llm_analysis/llm_change_analysis.csv`: local LLM change notes |
| What value/thematic categories are present | `outputs/part1_company_year.csv`: `theme_categories`, `theme_evidence`; `outputs/theme_observations.csv`: long-format phrase evidence; `docs/taxonomy.md`: category definitions and justification; `outputs/llm_analysis/llm_snapshot_analysis.csv`: local LLM snapshot notes |
| Notable linguistic shifts over time | `outputs/part1_company_year.csv`: `linguistic_metrics`, `linguistic_shift_notes`; `outputs/change_events.csv`: adjacent-year change evidence; `outputs/llm_analysis/llm_change_analysis.csv`: local LLM linguistic-shift notes |

`outputs/llm_analysis/llm_analysis_summary.json` records model, prompt, package-version, hash,
device, and coverage metadata for the local LLM layer.

## Script Task Map

The Part 1 code is organized around a few large reproducible tasks. Command-line modules execute
the workflow, while support modules hold reusable Wayback collection, extraction, and analysis
logic.

<table>
  <thead>
    <tr>
      <th>Large task</th>
      <th>Script/module</th>
      <th>Executes which task</th>
      <th>Function of the script/module</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Target setup</td>
      <td><code>src/org_auth_part1/targets.py</code></td>
      <td>Builds <code>data/processed/target_company_years.csv</code>.</td>
      <td>Loads the fixed 50-company manifest and expands it into the 2016-2024 company-year target grid.</td>
    </tr>
    <tr>
      <td>Candidate registry</td>
      <td><code>src/org_auth_part1/registry.py</code></td>
      <td>Validates reviewed page candidates.</td>
      <td>Checks that every required company has reviewed official page candidates and that registry rows obey the expected schema.</td>
    </tr>
    <tr>
      <td rowspan="5">Wayback discovery and snapshot selection</td>
      <td><code>src/org_auth_part1/run.py</code></td>
      <td>Runs the complete Part 1 workflow.</td>
      <td>Orchestrates target setup, registry validation, historical URL discovery, CDX querying, annual snapshot selection, replay/extraction, final audits, and phase validation with resumable progress logs.</td>
    </tr>
    <tr>
      <td><code>src/org_auth_part1/discover.py</code></td>
      <td>Discovers candidate captures and historical URLs.</td>
      <td>Queries Wayback CDX using exact URL lookup, documented prefix fallback, and historical candidate expansion; writes CDX query logs, annual candidate rows, and historical discovery audit files.</td>
    </tr>
    <tr>
      <td><code>src/org_auth_part1/cdx.py</code></td>
      <td>Supports Wayback CDX API access.</td>
      <td>Wraps CDX query parameters, retry behavior, response parsing, and capture metadata normalization.</td>
    </tr>
    <tr>
      <td><code>src/org_auth_part1/acquire.py</code></td>
      <td>Selects annual snapshot candidates.</td>
      <td>Ranks same-year captures by eligibility, page semantics, and distance from the June 30 anchor; writes acquisition status and candidate-selection tables.</td>
    </tr>
    <tr>
      <td><code>src/org_auth_part1/models.py</code></td>
      <td>Supports typed collection records.</td>
      <td>Defines shared company, target, candidate, capture, and analysis records used across collection stages.</td>
    </tr>
    <tr>
      <td rowspan="2">Replay retrieval and extraction</td>
      <td><code>src/org_auth_part1/pipeline.py</code></td>
      <td>Runs replay fetching, extraction, final dataset assembly, and baseline analysis.</td>
      <td>Fetches Wayback replay variants, extracts text, writes text artifacts, applies QA/gap rules, computes changes/themes/metrics, writes final CSVs, and refreshes audits and summary docs.</td>
    </tr>
    <tr>
      <td><code>src/org_auth_part1/extract.py</code></td>
      <td>Supports visible-text extraction.</td>
      <td>Removes navigation, scripts, styles, archive boilerplate, and error-like content; uses structural parsing plus controlled fallback extraction and emits QA metrics.</td>
    </tr>
    <tr>
      <td rowspan="2">Deterministic analysis</td>
      <td><code>src/org_auth_part1/compare.py</code></td>
      <td>Supports adjacent-year change detection.</td>
      <td>Compares only adjacent usable company-year text within each ticker and returns exact-match, similarity, word-count change, representative differences, and magnitude labels.</td>
    </tr>
    <tr>
      <td><code>src/org_auth_part1/analyze.py</code></td>
      <td>Supports theme and linguistic baseline coding.</td>
      <td>Applies the fixed stated-values taxonomy, records literal phrase evidence, and computes deterministic lexical language/tone metrics.</td>
    </tr>
    <tr>
      <td>Local LLM analysis</td>
      <td><code>src/org_auth_part1/llm_analysis.py</code></td>
      <td>Runs auditable open-source LLM annotations.</td>
      <td>Uses cached <code>Qwen/Qwen3-1.7B</code> by default, builds deterministic excerpts and prompts, generates snapshot/change notes, strips hidden-reasoning wrappers, records hashes, package versions, device metadata, and quality flags.</td>
    </tr>
    <tr>
      <td rowspan="3">Reporting and validation</td>
      <td><code>src/org_auth_part1/report.py</code></td>
      <td>Supports coverage and requirement audits.</td>
      <td>Builds coverage summaries, structural requirement checks, and human-readable summary payloads from the final dataset.</td>
    </tr>
    <tr>
      <td><code>src/org_auth_part1/validate.py</code></td>
      <td>Validates final output contract.</td>
      <td>Checks required rows, keys, field presence, usable-source evidence, non-usable gap reasons, theme evidence, and analysis output consistency.</td>
    </tr>
    <tr>
      <td><code>src/org_auth_part1/phase_validation.py</code></td>
      <td>Validates Phase 0-7 completion gates.</td>
      <td>Audits target contract, registry coverage, CDX completion, extraction/review status, change outputs, theme/LLM analysis, and reporting deliverables.</td>
    </tr>
    <tr>
      <td>Monitoring</td>
      <td><code>src/org_auth_part1/status.py</code></td>
      <td>Summarizes live Part 1 run progress.</td>
      <td>Reads the JSONL progress log and state file to report current stage, latest event, company-year progress, and resume context.</td>
    </tr>
    <tr>
      <td>Quality assurance</td>
      <td><code>tests/</code></td>
      <td>Runs Part 1 unit and phase tests.</td>
      <td>Tests target construction, registry validation, CDX behavior, snapshot selection, extraction QA, change detection, deterministic analysis, LLM routing, run orchestration, status reporting, and phase validation.</td>
    </tr>
  </tbody>
</table>

## Required Final Fields

| Field | Meaning |
|---|---|
| `ticker` | Required company ticker |
| `company_name` | Required company name |
| `sector` | Required GICS sector grouping |
| `year` | Target calendar year, 2016–2024 |
| `page_text_clean` | Extracted substantive body text |
| `changed_from_prior` | Whether cleaned text changed substantively from the immediately prior year; null when comparison is unavailable |
| `theme_categories` | Evidence-backed multi-label theme categories |
| `analyst_notes` | Concise interpretation and limitations |

## Provenance and Quality Fields

| Field | Meaning |
|---|---|
| `observation_status` | Controlled collection/extraction status |
| `gap_reason` | Structured explanation for non-usable rows |
| `candidate_url` | Reviewed URL used in CDX discovery |
| `source_url` | Original archived URL |
| `wayback_url` | Replay URL for the selected capture |
| `capture_timestamp` | Wayback capture timestamp |
| `selection_distance_days` | Distance from annual June 30 anchor |
| `raw_content_sha256` | Hash of replayed HTML |
| `clean_text_sha256` | Hash of cleaned substantive text |
| `extraction_quality` | Quality classification or score |
| `change_score` | Continuous adjacent-year change score |
| `change_magnitude` | Interpretable change class |
| `manual_review_status` | Whether human review is pending or complete |

## Local LLM Analysis Outputs

`outputs/llm_analysis/llm_snapshot_analysis.csv` contains one row per company-year. Usable rows
receive local LLM notes; non-usable rows are retained with `analysis_status = skipped_nonusable`.

| Field | Meaning |
|---|---|
| `analysis_status` | `completed` for generated LLM rows; otherwise an explicit skip reason |
| `model_name` | Open-source model used for generated rows |
| `prompt_version` | Versioned prompt template identifier |
| `input_text_sha256` | Hash of the clean text used to derive the excerpt |
| `prompt_sha256` | Hash of the exact prompt sent to the local model |
| `response_sha256` | Hash of the generated response |
| `input_excerpt` | Deterministic value-relevant excerpt used in the prompt |
| `llm_response` | Raw local-model response |
| `annotation_quality_flag` | Heuristic flag for whether the response is interpretable |

`outputs/llm_analysis/llm_change_analysis.csv` contains one row per company-year, with generated
LLM notes only when both the current and prior year are usable. It additionally records
`prior_year`, baseline change fields, prior/current text hashes, and prior/current excerpts.

`outputs/llm_analysis/llm_analysis_summary.json` records model settings, model family, local-file
policy, Torch device, package versions, input and output hashes, coverage counts, quality counts,
and the interpretation policy for the LLM layer. The current submitted run uses cached
`Qwen/Qwen3-1.7B` through the `causal-chat` path on Apple MPS.
