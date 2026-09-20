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
    """The review reduced seven modules to five. A sixth is a plan change, not a refactor.

    ``__main__`` is not one: it is ``python -m carb3``, the entry point, and it holds no
    model code — argument parsing, the order the five stages run in, and the run report
    §5.2 and §5.3 ask to be printed. Dunder modules are excluded by name rather than
    listed, so adding ``carb3/sixth.py`` still fails this.
    """
    package_dir = __import__("pathlib").Path(carb3.__file__).parent
    modules = {
        path.stem
        for path in package_dir.glob("*.py")
        if not path.stem.startswith("__")
    }
    assert modules == set(MODULE_NAMES)


def test_the_entry_point_is_runnable() -> None:
    """``python -m carb3`` needs a ``__main__`` with a ``main`` that returns an exit code."""
    entry = importlib.import_module("carb3.__main__")
    assert callable(entry.main)
    assert entry.DEFAULT_PREMISES == ("mvp-minimal", "mvp-dairy", "mvp-cement")
