from paa.render.view_models import (
    escape_display,
    format_display_value,
    format_local_datetime,
    humanize_label,
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

