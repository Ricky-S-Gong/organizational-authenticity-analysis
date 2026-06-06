# Pilot Decision Record

## Scope

The pilot exercised the complete pipeline across the available live CDX responses and replayed selected snapshots. It validated page registry rules, deterministic annual selection, replay retrieval, extraction, change detection, theme analysis, and final reporting.

## Locked Decisions

- Use official parent-company identity, mission, purpose, values, About Us, or equivalent overview pages.
- Select the successful HTML capture nearest June 30 at 12:00 UTC.
- Do not substitute adjacent-year captures.
- Keep `review` candidates out of automatic acquisition until approved.
- Preserve every company-year as an explicit status row.
- Treat short, error-like, empty, or failed replay content as non-usable.
- Compare only adjacent calendar years.
- Require evidence for deterministic theme classifications.
- Preserve manual review as a formal queue.

## Pilot Findings

- The 50-company candidate registry is structurally valid.
- Deterministic selection and extraction worked for the live captures that Wayback returned.
- Wayback CDX returned widespread `503 Service Unavailable`, connection-refused, and timeout errors. These are classified as `discovery_incomplete`.
- The live run does not meet the intended coverage threshold and must be resumed when Wayback is available.
- No external LLM credentials were available. The deterministic evidence-backed taxonomy baseline is complete, but the LLM completion gate remains open.

## Scale Decision

The pipeline is approved for resumable scale-up because failures are explicit, caching is deterministic, and all downstream stages can be regenerated. The current data run is not approved as a fully complete research result until discovery gaps and the LLM gate are resolved.
