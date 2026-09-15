from __future__ import annotations

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--update-goldens",
        action="store_true",
        default=False,
        help="Update Aurora text golden snapshots from the deterministic fixture renderer.",
    )


@pytest.fixture()
def update_goldens(pytestconfig: pytest.Config) -> bool:
    return bool(pytestconfig.getoption("--update-goldens"))
