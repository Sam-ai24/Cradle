from __future__ import annotations


class NotConfiguredError(RuntimeError):
    """Raised by any plugin (data connector, simulation adapter, AI model
    adapter) when it can't run because required external configuration —
    an API key, a credential, a license acknowledgment — is absent, as
    distinct from a bug in the plugin itself. The conformance runner
    reports this as a skip, not a failure: a fresh environment without
    (say) a registered BioGRID key can't test that connector, and that
    isn't the same kind of problem as a connector that's actually broken.
    """
