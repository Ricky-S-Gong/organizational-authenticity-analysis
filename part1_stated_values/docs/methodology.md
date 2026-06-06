# Part 1 Methodology

## Research Unit

The target unit is one company-year for each required company from 2016 through 2024. The master target grid contains exactly 450 rows, including explicit records for missing or unusable observations.

## Eligible Pages

Eligible pages are official parent-company pages primarily describing corporate identity, mission, purpose, or values. The preference hierarchy is:

1. mission, purpose, or values page
2. corporate About Us or Who We Are page
3. equivalent corporate overview page

Product, subsidiary, careers, newsroom, campaign, and third-party pages are excluded. Multiple historical URLs may represent the same page function, but every transition must be documented.

## Annual Snapshot Rule

For each eligible candidate and target year, select the usable HTML capture closest to June 30 at 12:00 UTC. Ties prefer the earlier capture, then the lexicographically earlier original URL.

Captures from adjacent years are never substituted. If no usable target-year capture exists, the row remains non-usable with a structured gap reason.

## Acquisition

CDX queries retain timestamp, original URL, status code, MIME type, digest, and content length. Broad discovery metadata is retained before replay retrieval. Collection is resumable and every target company-year receives a status.

## Extraction

Archived HTML is parsed structurally. Scripts, styles, forms, navigation, footers, cookie notices, and common archive boilerplate are removed. The pipeline preserves substantive headings and paragraphs, records content hashes and text metrics, and flags suspicious results for manual review.

## Change Detection

Change is calculated only from cleaned substantive text for adjacent calendar years. The pipeline retains exact match, continuous similarity, word-count change, representative additions/removals, and an interpretable change class. If either adjacent year is unusable, `changed_from_prior` is null.

## Theme and Linguistic Analysis

The reproducible baseline uses a fixed, multi-label taxonomy with evidence-backed phrase rules and deterministic linguistic metrics. Theme classifications retain evidence and salience. An LLM-assisted structured classifier can be added when credentials are available, but no LLM result is claimed unless model, prompt, and run metadata are recorded.

## Validation

Each phase has automated tests. The final pipeline also produces:

- a 450-row requirement audit
- coverage and failure summaries
- manual review queues
- extraction and change QA flags
- evidence-backed theme observations

Manual corrections must be recorded rather than silently overwriting generated values.
