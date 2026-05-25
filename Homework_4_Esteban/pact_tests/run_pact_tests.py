#!/usr/bin/env python3
"""Docker entrypoint for the Pact test suite.

Runs the complete consumer-driven contract testing flow inside the container:

1. Wait until the Catalog and Ticketing providers are reachable.
2. Run the consumer tests, which generate the Pact contracts under ``pacts/``.
3. Run the provider verification, which replays those contracts against the
   live Catalog and Ticketing services.

The process exits with a non-zero status if any step fails, so it works as a
CI gate (``docker compose ... run`` propagates the exit code).
"""

import os
import subprocess
import sys
import time
import urllib.request

CATALOG_BASE_URL = os.getenv("CATALOG_BASE_URL", "http://catalog:8000")
TICKETING_BASE_URL = os.getenv("TICKETING_BASE_URL", "http://ticketing:8000")


def _is_ready(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            return response.status == 200
    except Exception:
        return False


def wait_for_providers(attempts: int = 30, delay: int = 2) -> None:
    print(
        f"==> Waiting for Catalog ({CATALOG_BASE_URL}) and "
        f"Ticketing ({TICKETING_BASE_URL})...",
        flush=True,
    )
    for attempt in range(1, attempts + 1):
        if _is_ready(f"{CATALOG_BASE_URL}/events") and _is_ready(
            f"{TICKETING_BASE_URL}/orders"
        ):
            print("==> Providers are ready.", flush=True)
            return
        print(f"   ...not ready yet (attempt {attempt}/{attempts})", flush=True)
        time.sleep(delay)
    print("!! Providers did not become ready in time; continuing anyway.", flush=True)


def run_pytest(label: str, *pytest_args: str) -> int:
    print("\n" + "=" * 70)
    print(f" {label}")
    print("=" * 70, flush=True)
    return subprocess.call([sys.executable, "-m", "pytest", *pytest_args])


def main() -> int:
    wait_for_providers()

    consumer_rc = run_pytest(
        "STEP 1/2  Consumer tests  (generate the Pact contracts)",
        "consumer",
        "-v",
    )
    if consumer_rc != 0:
        print("\n!! Consumer tests failed; skipping provider verification.", flush=True)
        return consumer_rc

    provider_rc = run_pytest(
        "STEP 2/2  Provider verification  (replay contracts vs live APIs)",
        "provider",
        "-v",
    )
    return provider_rc


if __name__ == "__main__":
    sys.exit(main())
