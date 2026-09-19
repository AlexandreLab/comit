"""Shared fixtures for the carb3 tests.

Scaffolding stage: these tests assert that the five modules named in plan §5.1 exist and
expose the signatures T2-T8 will fill in. They deliberately do not exercise behaviour —
every public function still raises ``NotImplementedError``.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import pytest

#: The five modules of plan §5.1. The review reduced seven to five; a sixth is a plan change.
MODULE_NAMES: tuple[str, ...] = ("load", "sets", "survival", "build", "ledger")


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """The comit repository root, derived from this file's location."""
    return Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def reference_root(repo_root: Path) -> Path:
    """``docs/notes/data/`` — read, never written (plan §3)."""
    return repo_root / "docs" / "notes" / "data"


@pytest.fixture
def assert_signature() -> Callable[[ModuleType, str, tuple[str, ...]], None]:
    """Assert a module exposes a callable with exactly the given parameter names."""

    def _assert(module: ModuleType, name: str, parameters: tuple[str, ...]) -> None:
        member = getattr(module, name, None)
        assert member is not None, f"{module.__name__}.{name} is missing"
        assert callable(member), f"{module.__name__}.{name} is not callable"
        actual = tuple(inspect.signature(member).parameters)
        assert actual == parameters, (
            f"{module.__name__}.{name}{actual} does not match the planned "
            f"signature {parameters}"
        )

    return _assert


@pytest.fixture
def assert_not_implemented() -> Callable[[Callable[..., object]], None]:
    """Assert a scaffolded function still raises ``NotImplementedError``."""

    def _assert(func: Callable[..., object]) -> None:
        with pytest.raises(NotImplementedError):
            func()

    return _assert
