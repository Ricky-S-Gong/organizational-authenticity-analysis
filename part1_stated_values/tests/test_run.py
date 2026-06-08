from pathlib import Path

from org_auth_part1 import run


def test_parse_only_statuses_accepts_repeated_and_comma_separated_values() -> None:
    assert run.parse_only_statuses(
        ["retrieval_failed,insufficient_substantive_text", "no_cdx_capture"]
    ) == {
        "retrieval_failed",
        "insufficient_substantive_text",
        "no_cdx_capture",
    }


def test_parse_only_statuses_returns_none_for_empty_values() -> None:
    assert run.parse_only_statuses(["", " , "]) is None


def test_run_all_orchestrates_complete_workflow(monkeypatch, tmp_path: Path) -> None:
    calls = []

    monkeypatch.setattr(run, "load_companies", lambda path: ["company"])
    monkeypatch.setattr(run, "build_targets", lambda companies: ["target"])

    def write_target_grid(targets, output_path):
        calls.append(("targets", len(targets), output_path))

    monkeypatch.setattr(run, "write_target_grid", write_target_grid)
    monkeypatch.setattr(run, "load_candidates", lambda path: ["candidate"])
    monkeypatch.setattr(
        run,
        "validate_registry",
        lambda candidates, companies_path: {
            "companies": 1,
            "candidates": 1,
            "eligible_candidates": 1,
        },
    )

    def discover_candidates(*args, **kwargs):
        calls.append(("discover", kwargs["prefix_fallback"], kwargs["force"]))
        return [{"year_records": []}]

    monkeypatch.setattr(run, "discover_candidates", discover_candidates)
    monkeypatch.setattr(run, "query_log_rows", lambda records, cache_dir: [])
    monkeypatch.setattr(
        run,
        "write_query_log",
        lambda rows, path: calls.append(("query_log", path)),
    )
    monkeypatch.setattr(
        run,
        "build_annual_outputs",
        lambda *args: ([{"candidate": 1}], [{"status": 1}]),
    )
    monkeypatch.setattr(run, "write_csv", lambda rows, path, fields: calls.append(("csv", path)))

    def run_pipeline(status_output, **kwargs):
        calls.append(("pipeline", status_output, kwargs))
        return [{"final": 1}]

    monkeypatch.setattr(run, "run_pipeline", run_pipeline)

    def build_requirement_audit(targets_path, final_dataset):
        calls.append(("requirement_audit", targets_path, final_dataset))
        return {"passed": True}

    monkeypatch.setattr(run, "build_requirement_audit", build_requirement_audit)
    monkeypatch.setattr(run, "validate_phases", lambda root: {"passed": True})

    summary = run.run_all(
        companies_path=tmp_path / "companies.csv",
        candidates_path=tmp_path / "candidates.csv",
        targets_path=tmp_path / "targets.csv",
        cache_dir=tmp_path / "cache",
        query_log_path=tmp_path / "query_log.csv",
        progress_log=tmp_path / "progress.jsonl",
        state_file=tmp_path / "state.json",
        replay_retries=2,
        force_discovery=True,
        workers=2,
        fetch_timeout_seconds=90,
        fetch_retries=7,
        fetch_backoff_seconds=0.25,
        force_fetch=True,
        alternate_recovery_passes=0,
        enable_trafilatura_fallback=True,
        enable_wayback_json_api_fallback=True,
    )

    assert summary["targets"] == 1
    assert summary["phase_validation_passed"] is True
    assert ("discover", True, True) in calls
    assert ("query_log", tmp_path / "query_log.csv") in calls
    assert ("requirement_audit", tmp_path / "targets.csv", run.DEFAULT_FINAL) in calls
    pipeline_calls = [call for call in calls if call[0] == "pipeline"]
    assert len(pipeline_calls) == 2
    assert pipeline_calls[0][2]["workers"] == 2
    assert pipeline_calls[0][2]["fetch_timeout_seconds"] == 90
    assert pipeline_calls[0][2]["fetch_retries"] == 7
    assert pipeline_calls[0][2]["fetch_backoff_seconds"] == 0.25
    assert pipeline_calls[0][2]["force_fetch"] is True
    assert pipeline_calls[0][2]["enable_trafilatura_fallback"] is True
    assert pipeline_calls[0][2]["enable_wayback_json_api_fallback"] is True
    assert (tmp_path / "progress.jsonl").exists()
    assert (tmp_path / "state.json").exists()


def test_run_all_can_scope_network_work_to_nonusable_rows(monkeypatch, tmp_path: Path) -> None:
    calls = []

    monkeypatch.setattr(run, "load_companies", lambda path: ["company"])
    monkeypatch.setattr(run, "build_targets", lambda companies: ["target"])
    monkeypatch.setattr(run, "write_target_grid", lambda targets, output_path: None)
    monkeypatch.setattr(run, "load_candidates", lambda path: ["candidate"])
    monkeypatch.setattr(
        run,
        "validate_registry",
        lambda candidates, companies_path: {
            "companies": 1,
            "candidates": 1,
            "eligible_candidates": 1,
        },
    )
    monkeypatch.setattr(run, "load_nonusable_keys", lambda final_path: {("AAA", 2020)})

    def discover_candidates(*args, **kwargs):
        calls.append(("discover", kwargs["target_keys"]))
        return [{"year_records": []}]

    monkeypatch.setattr(run, "discover_candidates", discover_candidates)
    monkeypatch.setattr(run, "query_log_rows", lambda records, cache_dir: [])
    monkeypatch.setattr(run, "merge_query_log_rows", lambda path, rows: rows)
    monkeypatch.setattr(run, "write_query_log", lambda rows, path: None)
    monkeypatch.setattr(run, "build_annual_outputs", lambda *args: ([], []))
    monkeypatch.setattr(run, "write_csv", lambda rows, path, fields: None)

    def run_pipeline(status_output, **kwargs):
        calls.append(("pipeline", kwargs["target_keys"]))
        return [{"final": 1}]

    monkeypatch.setattr(run, "run_pipeline", run_pipeline)
    monkeypatch.setattr(run, "build_requirement_audit", lambda *args: {"passed": True})
    monkeypatch.setattr(run, "validate_phases", lambda root: {"passed": True})

    run.run_all(
        companies_path=tmp_path / "companies.csv",
        candidates_path=tmp_path / "candidates.csv",
        targets_path=tmp_path / "targets.csv",
        cache_dir=tmp_path / "cache",
        query_log_path=tmp_path / "query_log.csv",
        progress_log=tmp_path / "progress.jsonl",
        state_file=tmp_path / "state.json",
        only_nonusable=True,
        alternate_recovery_passes=0,
    )

    assert ("discover", {("AAA", 2020)}) in calls
    assert ("pipeline", {("AAA", 2020)}) in calls


def test_run_all_can_scope_network_work_to_specific_statuses(monkeypatch, tmp_path: Path) -> None:
    calls = []

    monkeypatch.setattr(run, "load_companies", lambda path: ["company"])
    monkeypatch.setattr(run, "build_targets", lambda companies: ["target"])
    monkeypatch.setattr(run, "write_target_grid", lambda targets, output_path: None)
    monkeypatch.setattr(run, "load_candidates", lambda path: ["candidate"])
    monkeypatch.setattr(
        run,
        "validate_registry",
        lambda candidates, companies_path: {
            "companies": 1,
            "candidates": 1,
            "eligible_candidates": 1,
        },
    )
    monkeypatch.setattr(run, "load_status_keys", lambda statuses: {("AAA", 2020)})
    monkeypatch.setattr(
        run,
        "discover_candidates",
        lambda *args, **kwargs: calls.append(("discover", kwargs["target_keys"])) or [],
    )
    monkeypatch.setattr(run, "query_log_rows", lambda records, cache_dir: [])
    monkeypatch.setattr(
        run,
        "merge_query_log_rows",
        lambda path, rows: calls.append(("merge_query_log", path)) or rows,
    )
    monkeypatch.setattr(run, "write_query_log", lambda rows, path: None)
    monkeypatch.setattr(run, "build_annual_outputs", lambda *args: ([], []))
    monkeypatch.setattr(run, "write_csv", lambda rows, path, fields: None)
    monkeypatch.setattr(
        run,
        "run_pipeline",
        lambda status_output, **kwargs: calls.append(("pipeline", kwargs["target_keys"])) or [],
    )
    monkeypatch.setattr(run, "build_requirement_audit", lambda *args: {"passed": True})
    monkeypatch.setattr(run, "validate_phases", lambda root: {"passed": True})

    run.run_all(
        companies_path=tmp_path / "companies.csv",
        candidates_path=tmp_path / "candidates.csv",
        targets_path=tmp_path / "targets.csv",
        cache_dir=tmp_path / "cache",
        query_log_path=tmp_path / "query_log.csv",
        progress_log=tmp_path / "progress.jsonl",
        state_file=tmp_path / "state.json",
        only_statuses={"retrieval_failed"},
        alternate_recovery_passes=0,
    )

    assert ("discover", {("AAA", 2020)}) in calls
    assert ("pipeline", {("AAA", 2020)}) in calls
    assert ("merge_query_log", tmp_path / "query_log.csv") in calls


def test_run_all_can_discover_historical_urls_before_cdx_collection(
    monkeypatch, tmp_path: Path
) -> None:
    calls = []
    augmented = tmp_path / "augmented.csv"

    monkeypatch.setattr(run, "load_companies", lambda path: ["company"])
    monkeypatch.setattr(run, "build_targets", lambda companies: ["target"])
    monkeypatch.setattr(run, "write_target_grid", lambda targets, output_path: None)
    monkeypatch.setattr(run, "load_nonusable_keys", lambda final_path: {("AAA", 2020)})
    monkeypatch.setattr(run, "load_status_keys", lambda statuses: {("AAA", 2020)})

    def discover_historical_page_candidates(*args, **kwargs):
        calls.append(("historical", kwargs["target_keys"]))
        calls.append(("historical_require_probe", kwargs["require_url_variant_cdx_capture"]))
        calls.append(("historical_probe_retries", kwargs["url_variant_probe_retries"]))
        calls.append(("historical_probe_backoff", kwargs["url_variant_probe_backoff_seconds"]))
        calls.append(("historical_probe_sleep", kwargs["url_variant_probe_sleep_seconds"]))
        return ([{"ticker": "AAA"}], [{"ticker": "AAA"}])

    monkeypatch.setattr(
        run,
        "discover_historical_page_candidates",
        discover_historical_page_candidates,
    )
    monkeypatch.setattr(
        run,
        "merge_candidate_files",
        lambda seed, generated, output: calls.append(("merge", seed, generated, output)) or [],
    )
    monkeypatch.setattr(run, "load_candidates", lambda path: calls.append(("load", path)) or [])
    monkeypatch.setattr(
        run,
        "validate_registry",
        lambda candidates, companies_path: {
            "companies": 1,
            "candidates": 1,
            "eligible_candidates": 1,
        },
    )

    def discover_candidates(candidates_path, *args, **kwargs):
        calls.append(("discover", candidates_path, kwargs["target_keys"]))
        calls.append(("discover_availability_fallback", kwargs["availability_fallback"]))
        return [{"year_records": []}]

    monkeypatch.setattr(run, "discover_candidates", discover_candidates)
    monkeypatch.setattr(run, "query_log_rows", lambda records, cache_dir: [])
    monkeypatch.setattr(run, "merge_query_log_rows", lambda path, rows: rows)
    monkeypatch.setattr(run, "write_query_log", lambda rows, path: None)
    monkeypatch.setattr(run, "build_annual_outputs", lambda *args: ([], []))
    monkeypatch.setattr(run, "write_csv", lambda rows, path, fields: None)
    monkeypatch.setattr(run, "run_pipeline", lambda *args, **kwargs: [{"final": 1}])
    monkeypatch.setattr(run, "build_requirement_audit", lambda *args: {"passed": True})
    monkeypatch.setattr(run, "validate_phases", lambda root: {"passed": True})

    summary = run.run_all(
        companies_path=tmp_path / "companies.csv",
        candidates_path=tmp_path / "seed.csv",
        targets_path=tmp_path / "targets.csv",
        cache_dir=tmp_path / "cache",
        query_log_path=tmp_path / "query_log.csv",
        progress_log=tmp_path / "progress.jsonl",
        state_file=tmp_path / "state.json",
        only_nonusable=True,
        alternate_recovery_passes=0,
        enable_wayback_json_api_fallback=True,
        discover_historical_urls=True,
        require_url_variant_cdx_capture=True,
        url_variant_probe_retries=7,
        url_variant_probe_backoff_seconds=4.0,
        url_variant_probe_sleep_seconds=0.5,
        historical_candidates_path=tmp_path / "historical.csv",
        historical_discovery_audit_path=tmp_path / "audit.csv",
        augmented_candidates_path=augmented,
    )

    assert ("historical", {("AAA", 2020)}) in calls
    assert ("historical_require_probe", True) in calls
    assert ("historical_probe_retries", 7) in calls
    assert ("historical_probe_backoff", 4.0) in calls
    assert ("historical_probe_sleep", 0.5) in calls
    assert ("load", augmented) in calls
    assert ("discover", augmented, {("AAA", 2020)}) in calls
    assert ("discover_availability_fallback", True) in calls
    assert summary["historical_discovery"]["generated_candidates"] == 1
    assert summary["historical_discovery"]["url_variant_cdx_capture_required"] is True
    assert summary["historical_discovery"]["url_variant_probe_retries"] == 7


def test_alternate_capture_recovery_selects_next_eligible_same_year_capture() -> None:
    status_rows = [
        {
            "ticker": "AAA",
            "year": "2020",
            "acquisition_status": "selected",
            "failure_reason": "",
            "selected_capture_timestamp": "2020-06-30T12:00:00+00:00",
            "selected_original_url": "https://example.com/about",
            "selected_replay_url": "https://web.archive.org/web/20200630120000id_/a",
        },
        {
            "ticker": "BBB",
            "year": "2020",
            "acquisition_status": "selected",
            "failure_reason": "",
            "selected_capture_timestamp": "2020-06-30T12:00:00+00:00",
            "selected_original_url": "https://example.org/about",
            "selected_replay_url": "https://web.archive.org/web/20200630120000id_/b",
        },
    ]
    candidate_rows = [
        {
            "ticker": "AAA",
            "year": "2020",
            "rank": "1",
            "eligible": "True",
            "capture_timestamp": "2020-06-30T12:00:00+00:00",
            "original_url": "https://example.com/about",
            "replay_url": "https://web.archive.org/web/20200630120000id_/a",
        },
        {
            "ticker": "AAA",
            "year": "2020",
            "rank": "2",
            "eligible": "True",
            "capture_timestamp": "2020-07-15T12:00:00+00:00",
            "original_url": "https://example.com/about",
            "replay_url": "https://web.archive.org/web/20200715120000id_/a",
        },
        {
            "ticker": "BBB",
            "year": "2020",
            "rank": "2",
            "eligible": "True",
            "capture_timestamp": "2020-07-15T12:00:00+00:00",
            "original_url": "https://example.org/about",
            "replay_url": "https://web.archive.org/web/20200715120000id_/b",
        },
    ]
    final_rows = [
        {"ticker": "AAA", "year": "2020", "observation_status": "insufficient_substantive_text"},
        {"ticker": "BBB", "year": "2020", "observation_status": "usable"},
    ]

    updated, keys = run.apply_alternate_capture_recovery(
        status_rows,
        candidate_rows,
        final_rows,
    )

    assert keys == {("AAA", 2020)}
    assert updated[0]["selected_replay_url"] == "https://web.archive.org/web/20200715120000id_/a"
    assert updated[1]["selected_replay_url"] == "https://web.archive.org/web/20200630120000id_/b"


def test_alternate_capture_recovery_only_moves_forward_in_rank() -> None:
    status_rows = [
        {
            "ticker": "AAA",
            "year": "2020",
            "selected_replay_url": "https://web.archive.org/web/20200715120000id_/a",
        }
    ]
    candidate_rows = [
        {
            "ticker": "AAA",
            "year": "2020",
            "rank": "1",
            "eligible": "True",
            "capture_timestamp": "2020-06-30T12:00:00+00:00",
            "original_url": "https://example.com/about",
            "replay_url": "https://web.archive.org/web/20200630120000id_/a",
        },
        {
            "ticker": "AAA",
            "year": "2020",
            "rank": "2",
            "eligible": "True",
            "capture_timestamp": "2020-07-15T12:00:00+00:00",
            "original_url": "https://example.com/about",
            "replay_url": "https://web.archive.org/web/20200715120000id_/a",
        },
        {
            "ticker": "AAA",
            "year": "2020",
            "rank": "3",
            "eligible": "True",
            "capture_timestamp": "2020-08-01T12:00:00+00:00",
            "original_url": "https://example.com/about",
            "replay_url": "https://web.archive.org/web/20200801120000id_/a",
        },
    ]
    final_rows = [
        {"ticker": "AAA", "year": "2020", "observation_status": "insufficient_substantive_text"}
    ]

    updated, keys = run.apply_alternate_capture_recovery(status_rows, candidate_rows, final_rows)

    assert keys == {("AAA", 2020)}
    assert updated[0]["selected_replay_url"] == "https://web.archive.org/web/20200801120000id_/a"
