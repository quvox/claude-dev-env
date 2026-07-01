import math

import pytest

from mathkit.geometry import rect_area, circle_area


def test_rect_area():
    assert rect_area(3, 4) == 12


def test_rect_area_zero():
    assert rect_area(0, 5) == 0


def test_circle_area():
    assert circle_area(2) == pytest.approx(math.pi * 4)


def test_circle_area_unit():
    assert circle_area(1) == pytest.approx(math.pi)
