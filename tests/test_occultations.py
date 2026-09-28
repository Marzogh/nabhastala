from datetime import UTC, datetime, timedelta

import numpy as np

from paa.compute.occultations import (
    _bisect_contact,
    _contact_brackets,
    _group_nearby_indexes,
)


def test_group_nearby_indexes_separates_monthly_passes() -> None:
    assert _group_nearby_indexes([1, 2, 3, 40, 41]) == [[1, 2, 3], [40, 41]]


def test_contact_brackets_find_disappearance_and_reappearance() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    times = [start + timedelta(minutes=index) for index in range(6)]
    values = np.array([2.0, 1.0, -1.0, -2.0, 1.0, 2.0])

    brackets = _contact_brackets(times, values)

    assert brackets == ((times[1], times[2]), (times[3], times[4]))


def test_bisect_contact_converges_on_zero() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    expected = start + timedelta(seconds=37)

    contact = _bisect_contact(
        start,
        start + timedelta(minutes=1),
        lambda value: (value - expected).total_seconds(),
    )

    assert abs((contact - expected).total_seconds()) < 0.01
