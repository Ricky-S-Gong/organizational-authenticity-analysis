# Organizational Authenticity Take-Home Assessment

This repository contains the work for the Wharton-TAU Lab 2026 Research Assistant recruitment assignment on organizational authenticity and corporate value alignment.

## Project Status

Part 1 implementation is underway. The repository includes a reproducible `uv` environment,
the fixed company sample, data contracts, and the initial Wayback CDX selection pipeline.

## Repository Structure

```text
.
├── part1_stated_values/   # Wayback Machine collection and stated-values analysis
├── part2_lived_values/    # Corporate disclosure collection and text analysis
├── part3_authenticity/    # Organizational Authenticity Index
├── part4_proposal/        # Additional analysis
├── src/                   # Installable Python source
├── pyproject.toml         # Project and tool configuration
├── uv.lock                # Locked Python environment
└── README.md
```

Each part will eventually contain its own README, code, output data, and written summary, as required by the assignment.

## Development

```bash
uv sync --no-editable
uv run --no-sync pytest
uv run --no-sync ruff check .
```
