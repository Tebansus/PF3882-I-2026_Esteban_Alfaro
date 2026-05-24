"""Provider verification: the live **Ticketing** service must honour the contract
recorded by the **Access Control** consumer (``pacts/accesscontrol-ticketing.json``).

Requires the Ticketing service to be running with ``PACT_PROVIDER_STATES=true`` so
the verifier can seed orders before each interaction via the
``/_pact/provider_states`` endpoint.

    TICKETING_BASE_URL   default http://localhost:8002 (local) / http://ticketing:8000 (docker)
"""

import os

import pytest
from pact import Verifier

PACT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pacts")
PACT_FILE = os.path.join(PACT_DIR, "accesscontrol-ticketing.json")
TICKETING_BASE_URL = os.getenv("TICKETING_BASE_URL", "http://localhost:8002")


@pytest.mark.skipif(
    not os.path.exists(PACT_FILE),
    reason="accesscontrol-ticketing.json not generated yet; run the consumer tests first.",
)
def test_ticketing_honours_access_control_contract():
    verifier = Verifier(provider="Ticketing", provider_base_url=TICKETING_BASE_URL)

    success, logs = verifier.verify_pacts(
        PACT_FILE,
        provider_states_setup_url=f"{TICKETING_BASE_URL}/_pact/provider_states",
        verbose=False,
    )

    assert success == 0, logs
