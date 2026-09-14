import pytest

from paa.render.view_models import (
    AnnualOverviewView,
    MonthGuideView,
    MonthSummaryView,
    OpportunityView,
    escape_display,
    format_display_value,
    format_local_datetime,
    humanize_label,
    opportunity_is_eligible,
    rank_opportunities,
    rating_tone,
)


def test_labels_are_human_readable() -> None:
    assert humanize_label("best_altitude_deg") == "Best altitude deg"
    assert humanize_label("moon_illumination_fraction") == "Moon illumination"


def test_iso_datetime_is_presented_for_people() -> None:
    assert format_local_datetime("2027-01-01T19:14:00+10:00") == "1 Jan 2027, 7:14 pm UTC+10:00"


def test_display_values_handle_missing_boolean_fraction_and_rating() -> None:
    assert format_display_value("target", "") == "—"
    assert format_display_value("is_planetary", "True") == "Yes"
    assert format_display_value("moon_illumination_fraction", "0.27") == "27%"
    assert format_display_value("rating", "query_failed") == "Query failed"


def test_rating_tones_are_semantic_and_unknown_values_are_neutral() -> None:
    assert rating_tone("excellent") == "excellent"
    assert rating_tone("query_failed") == "unavailable"
    assert rating_tone("unexpected") == "neutral"


def test_display_text_is_safely_escaped() -> None:
    assert escape_display('<script src="x">') == "&lt;script src=&quot;x&quot;&gt;"


def _opportunity(
    key: str,
    *,
    rating: str = "good",
    score: float | None = 3,
    date_local: str = "2027-01-10T20:00:00+10:00",
    source_order: int = 0,
    **changes: object,
) -> OpportunityView:
    values = {
        "key": key,
        "category": "planet",
        "title": key,
        "date_local": date_local,
        "rating": rating,
        "reason": "High after dark",
        "score": score,
        "source_order": source_order,
    }
    values.update(changes)
    return OpportunityView(**values)  # type: ignore[arg-type]


def test_highlight_eligibility_excludes_failed_incomplete_and_unobservable_records() -> None:
    assert opportunity_is_eligible(_opportunity("Jupiter"))
    assert not opportunity_is_eligible(_opportunity("failed", rating="query_failed"))
    assert not opportunity_is_eligible(_opportunity("missing", complete=False))
    assert not opportunity_is_eligible(_opportunity("hidden", observable=False))
    assert not opportunity_is_eligible(_opportunity("ordinary poor", rating="poor"))
    assert opportunity_is_eligible(
        _opportunity("notable poor", rating="poor", include_when_poor=True)
    )


def test_opportunities_rank_deterministically_and_can_be_filtered_by_month() -> None:
    candidates = [
        _opportunity("lower rating", rating="good", score=99, source_order=0),
        _opportunity("later", rating="excellent", score=5, date_local="2027-01-20"),
        _opportunity("tie second", rating="excellent", score=5, source_order=2),
        _opportunity("tie first", rating="excellent", score=5, source_order=1),
        _opportunity("February", rating="excellent", score=6, date_local="2027-02-01"),
    ]

    ranked = rank_opportunities(candidates, limit=3, month=1)

    assert [candidate.key for candidate in ranked] == ["tie first", "tie second", "later"]


def test_opportunity_ranking_validates_limit_and_month() -> None:
    with pytest.raises(ValueError, match="limit"):
        rank_opportunities([], limit=-1)
    with pytest.raises(ValueError, match="month"):
        rank_opportunities([], limit=3, month=0)


def test_annual_and_monthly_contracts_validate_collection_sizes() -> None:
    months = tuple(
        MonthSummaryView(
            month=month,
            verdict="Useful",
            rating="good",
            best_dark_window=None,
            moon_state="New Moon",
        )
        for month in range(1, 13)
    )
    annual = AnnualOverviewView(2027, "se_qld", "se-qld", months)
    monthly = MonthGuideView(2027, 1, "se_qld", "se-qld", "Useful")

    assert len(annual.months) == 12
    assert monthly.month == 1
    with pytest.raises(ValueError, match="months 1 through 12"):
        AnnualOverviewView(2027, "se_qld", "se-qld", months[:-1])
    with pytest.raises(ValueError, match="at most two"):
        MonthSummaryView(1, "Useful", "good", None, "New Moon", (_opportunity("x"),) * 3)
    with pytest.raises(ValueError, match="at most five"):
        MonthGuideView(2027, 1, "se_qld", "se-qld", "Useful", (_opportunity("x"),) * 6)
