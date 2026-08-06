"""Health check for the Battery Intelligence Platform API.

Fetches ``/api/health`` and validates the documented contract: HTTP 200 with
``status == "ok"``, plus ``service`` and ``version`` fields. Exits non-zero on
any failure so it can be used as a liveness/readiness probe.
"""

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

API_URL = os.environ.get("BIP_API_URL", "http://127.0.0.1:8100")
HEALTH_URL = f"{API_URL}/api/health"
EXPECTED_SERVICE = "Battery Intelligence Platform API"


def main() -> int:
    try:
        with urlopen(HEALTH_URL, timeout=5) as response:
            if response.status != 200:
                print(f"FAIL: HTTP {response.status}", file=sys.stderr)
                return 1
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        print(f"FAIL: HTTP {exc.code}", file=sys.stderr)
        return 1
    except (URLError, OSError) as exc:
        print(f"FAIL: cannot reach {HEALTH_URL}: {exc}", file=sys.stderr)
        return 1
    except json.JSONDecodeError:
        print("FAIL: response is not valid JSON", file=sys.stderr)
        return 1

    if payload.get("status") != "ok":
        print(f"FAIL: unexpected status {payload.get('status')!r}", file=sys.stderr)
        return 1
    if payload.get("service") != EXPECTED_SERVICE:
        print(f"FAIL: unexpected service {payload.get('service')!r}", file=sys.stderr)
        return 1
    if not payload.get("version"):
        print("FAIL: missing version", file=sys.stderr)
        return 1

    print(
        f"OK: {payload.get('service')} v{payload.get('version')} "
        f"({payload.get('environment')}) @ {payload.get('timestamp')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
