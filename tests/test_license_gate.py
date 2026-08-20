from __future__ import annotations

import pytest

from cradle.knowledge.gate import LicenseGate, LicenseNotAcknowledgedError


class _FakeRestrictedConnector:
    name = "fake-restricted"

    def fetch(self, curie: str):
        return {"curie": curie, "source": "Fake", "license": "Restricted", "data": {}}


def test_gate_refuses_until_acknowledged():
    gate = LicenseGate(_FakeRestrictedConnector(), "restricted for testing")
    with pytest.raises(LicenseNotAcknowledgedError):
        gate.fetch("fake:1")


def test_gate_delegates_once_acknowledged():
    gate = LicenseGate(_FakeRestrictedConnector(), "restricted for testing")
    gate.acknowledge()
    record = gate.fetch("fake:1")
    assert record["curie"] == "fake:1"


def test_gate_name_and_accepts_delegate_to_wrapped_connector():
    gate = LicenseGate(_FakeRestrictedConnector(), "restricted for testing")
    assert gate.name == "fake-restricted"
    assert gate.accepts("anything:at-all") is True  # no accepts() on the fake -> defaults True
