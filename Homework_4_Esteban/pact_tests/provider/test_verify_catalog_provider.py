"""Provider verification: the live **Catalog** service must honour the contract
recorded by the **Ticketing** consumer (``pacts/ticketing-catalog.json``).

Requires the Catalog service to be running with ``PACT_PROVIDER_STATES=true`` so
the verifier can reset the catalog before each interaction via the
``/_pact/provider_states`` endpoint.

    CATALOG_BASE_URL   default http://localhost:8001 (local) / http://catalog:8000 (docker)
"""

import os

import pytest
from pact import Verifier

PACT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pacts")
PACT_FILE = os.path.join(PACT_DIR, "ticketing-catalog.json")
CATALOG_BASE_URL = os.getenv("CATALOG_BASE_URL", "http://localhost:8001")


@pytest.mark.skipif(
    not os.path.exists(PACT_FILE),
    reason="ticketing-catalog.json not generated yet; run the consumer tests first.",
)
def test_catalog_honours_ticketing_contract():
    verifier = Verifier(provider="Catalog", provider_base_url=CATALOG_BASE_URL)

    success, logs = verifier.verify_pacts(
        PACT_FILE,
        provider_states_setup_url=f"{CATALOG_BASE_URL}/_pact/provider_states",
        verbose=False,
    )

    assert success == 0, logs
