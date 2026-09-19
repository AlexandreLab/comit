"""survival.py — D11 survival function, computed before the LP."""

from __future__ import annotations

import pytest

from carb3 import survival


def test_signatures(assert_signature) -> None:
    assert_signature(
        survival, "survival_fraction", ("install_year", "lifetime_years", "year")
    )
    assert_signature(survival, "surviving_capacity", ("vintages", "unit", "periods"))


def test_bodies_are_not_implemented_yet() -> None:
    with pytest.raises(NotImplementedError):
        survival.survival_fraction(2015, 25, 2030)
    with pytest.raises(NotImplementedError):
        survival.surviving_capacity(None, None, ())  # type: ignore[arg-type]
