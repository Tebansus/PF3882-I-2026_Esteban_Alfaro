"""Shared Pact fixtures and configuration for the consumer tests.

This file is imported automatically by pytest before any test runs, so it is
also where we make the ``pact_tests`` directory importable (so the test modules
can do ``from clients import CatalogClient``).
"""

import os
import sys

import pytest
from pact import Consumer, Provider

# Make ``clients.py`` (sibling of this conftest) importable from the test
# modules living in the ``consumer/`` sub-package.
sys.path.insert(0, os.path.dirname(__file__))

# All generated contracts are written here and later replayed by the provider
# verification step.
PACT_DIR = os.path.join(os.path.dirname(__file__), "pacts")

# The Pact mock server binds locally inside the test process / container.
MOCK_HOST = "127.0.0.1"
CATALOG_MOCK_PORT = 9150
TICKETING_MOCK_PORT = 9151


@pytest.fixture(scope="session")
def catalog_pact():
    """Contract: Ticketing (consumer) -> Catalog (provider)."""
    pact = Consumer("Ticketing").has_pact_with(
        Provider("Catalog"),
        host_name=MOCK_HOST,
        port=CATALOG_MOCK_PORT,
        pact_dir=PACT_DIR,
    )
    pact.start_service()
    yield pact
    pact.stop_service()


@pytest.fixture(scope="session")
def ticketing_pact():
    """Contract: Access Control (consumer) -> Ticketing (provider)."""
    pact = Consumer("AccessControl").has_pact_with(
        Provider("Ticketing"),
        host_name=MOCK_HOST,
        port=TICKETING_MOCK_PORT,
        pact_dir=PACT_DIR,
    )
    pact.start_service()
    yield pact
    pact.stop_service()
