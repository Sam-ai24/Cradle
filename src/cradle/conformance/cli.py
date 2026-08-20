from __future__ import annotations

import sys

from cradle.conformance.checks import CHECKS, ConformanceError
from cradle.contracts.errors import NotConfiguredError
from cradle.registry import discover_all


def main() -> int:
    """Discover every registered plugin and run its conformance check.

    This is the mechanism the roadmap's Phase 0 exit criterion refers to:
    a plugin of any kind can register via entry_points and be automatically
    verified against its contract, with no Cradle-core code change needed
    to add, remove, or swap it.
    """
    discovered = discover_all()
    failures = 0
    skipped = 0
    total = 0
    for kind, plugins in discovered.items():
        for plugin in plugins:
            total += 1
            label = f"{kind}:{plugin.entry_point_name} ({plugin.distribution})"
            try:
                CHECKS[kind](plugin.instance)
            except NotConfiguredError as exc:
                skipped += 1
                print(f"SKIP  {label} - {exc}")
            except ConformanceError as exc:
                failures += 1
                print(f"FAIL  {label} - {exc}")
            except Exception as exc:  # noqa: BLE001 - surface any adapter crash as a failure
                failures += 1
                print(f"ERROR {label} - {exc!r}")
            else:
                print(f"PASS  {label}")

    passed = total - failures - skipped
    print(f"\n{passed}/{total} plugins passed conformance ({skipped} skipped, not configured)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
