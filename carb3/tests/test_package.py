"""The package imports and holds exactly the five modules plan §5.1 names."""

from __future__ import annotations

import importlib

import carb3
from conftest import MODULE_NAMES


def test_package_version() -> None:
    assert carb3.__version__


def test_the_five_modules_import() -> None:
    for name in MODULE_NAMES:
        assert importlib.import_module(f"carb3.{name}") is not None


def test_no_sixth_module() -> None:
    """The review reduced seven modules to five. A sixth is a plan change, not a refactor."""
    package_dir = __import__("pathlib").Path(carb3.__file__).parent
    modules = {p.stem for p in package_dir.glob("*.py")} - {"__init__"}
    assert modules == set(MODULE_NAMES)
