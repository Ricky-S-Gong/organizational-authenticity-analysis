"""Summarize live Part 2 progress from the JSONL progress log."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from org_auth_part2.run import DEFAULT_PROGRESS_LOG, DEFAULT_STATE


def summarize(
    progress_log: Path = DEFAULT_PROGRESS_LOG,
    state_file: Path = DEFAULT_STATE,
) -> dict[str, object]:
    """Summarize append-only progress events plus the latest checkpoint state."""

    counts: dict[str, int] = {}
    latest: dict[str, object] = {}
    if progress_log.exists():
        with progress_log.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                event = json.loads(line)
                key = f"{event.get('stage')}:{event.get('status')}"
                counts[key] = counts.get(key, 0) + 1
                latest = event
    state = {}
    if state_file.exists():
        state = json.loads(state_file.read_text(encoding="utf-8"))
    return {"event_counts": counts, "latest_event": latest, "state": state}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Print Part 2 live collection status.")
    parser.add_argument("--progress-log", type=Path, default=DEFAULT_PROGRESS_LOG)
    parser.add_argument("--state-file", type=Path, default=DEFAULT_STATE)
    args = parser.parse_args(argv)
    print(json.dumps(summarize(args.progress_log, args.state_file), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
