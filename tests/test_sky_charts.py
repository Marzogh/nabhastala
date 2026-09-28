from pathlib import Path

import numpy as np
import pytest

from paa.render.sky_charts import (
    _compass_ring,
    generate_placeholder_sky_charts,
    project_altaz,
)


def test_project_altaz_places_cardinal_horizon_points() -> None:
    x, y = project_altaz(np.array([0, 0, 0, 0]), np.array([0, 90, 180, 270]))

    assert (x[0], y[0]) == pytest.approx((400, 70))
    assert (x[1], y[1]) == pytest.approx((70, 400))
    assert (x[2], y[2]) == pytest.approx((400, 730))
    assert (x[3], y[3]) == pytest.approx((730, 400))


def test_placeholder_chart_set_keeps_partial_render_links_valid(tmp_path: Path) -> None:
    outputs = generate_placeholder_sky_charts(year=2026, destination=tmp_path)

    assert len(outputs) == 12
    assert outputs[0].name == "month-01.svg"
    assert "Sky chart unavailable" in outputs[0].read_text(encoding="utf-8")


def test_compass_ring_includes_intercardinal_points_and_degree_bearings() -> None:
    ring = _compass_ring()

    assert ">NE<" in ring
    assert ">SW<" in ring
    assert ">30°<" in ring
    assert ring.count('class="bearing-tick"') == 72
