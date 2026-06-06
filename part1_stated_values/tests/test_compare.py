from org_auth_part1.compare import ChangeClass, compare_adjacent_years, compare_texts


def test_normalized_formatting_only_change_is_exactly_unchanged() -> None:
    result = compare_texts(
        "We serve customers.\nWe act with integrity.",
        "  we SERVE customers. We act with integrity.  ",
        year=2020,
        prior_year=2019,
    )

    assert result.change_class is ChangeClass.UNCHANGED_EXACT
    assert result.changed_from_prior is False
    assert result.exact_match is True
    assert result.added_snippets == ()
    assert result.removed_snippets == ()


def test_minor_edit_has_metrics_and_reviewable_evidence() -> None:
    prior = "We serve customers with integrity. We support employees and communities."
    current = "We serve customers with integrity. We support employees and local communities."

    result = compare_texts(prior, current, year=2020, prior_year=2019)

    assert result.change_class is ChangeClass.MINOR_EDIT
    assert result.changed_from_prior is True
    assert result.token_jaccard_similarity is not None
    assert result.token_jaccard_similarity >= 0.9
    assert result.added_snippets == ("We support employees and local communities.",)
    assert result.removed_snippets == ("We support employees and communities.",)


def test_substantive_change_captures_added_and_removed_sentences() -> None:
    result = compare_texts(
        "We maximize financial performance. Shareholder returns guide every decision.",
        "We protect the planet. Our communities and employees guide every decision.",
        year=2021,
        prior_year=2020,
    )

    assert result.change_class is ChangeClass.SUBSTANTIVE_CHANGE
    assert result.changed_from_prior is True
    assert "We protect the planet." in result.added_snippets
    assert "We maximize financial performance." in result.removed_snippets


def test_adjacent_year_comparison_does_not_bridge_missing_years() -> None:
    results = compare_adjacent_years(
        {
            2019: "We act with integrity.",
            2020: None,
            2021: "We act with integrity.",
        }
    )

    assert [result.change_class for result in results] == [
        ChangeClass.NO_PRIOR,
        ChangeClass.INDETERMINATE,
        ChangeClass.INDETERMINATE,
    ]
    assert results[2].prior_year == 2020
    assert results[2].changed_from_prior is None
