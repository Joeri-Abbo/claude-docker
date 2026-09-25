# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Schuberg Philis
"""--api blocks all egress; CLAUDE_DOCKER_EGRESS_POLICY is the only allowlist.

The policy file is parsed, and the model endpoint checked against it, before
container-runtime detection, so these cases need no docker. A policy that
passes both stops at the invalid CLAUDE_DOCKER_RUNTIME the helper sets.

Stdlib only, so CI's unit-test step keeps running with no install step.
"""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

RUN_SH = Path(__file__).resolve().parent.parent / "run.sh"


def run_api(policy=None, base_url="https://llm.example.eu/v1", policy_path=None):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("ANTHROPIC_", "CLAUDE_DOCKER_"))}
    env["ANTHROPIC_AUTH_TOKEN"] = "sk-test"
    # Rejected right after the policy checks, so a passing policy stops there
    # and never reaches a real engine.
    env["CLAUDE_DOCKER_RUNTIME"] = "none"
    if base_url:
        env["ANTHROPIC_BASE_URL"] = base_url
    with tempfile.TemporaryDirectory() as ws:
        if policy is not None:
            policy_path = os.path.join(ws, "egress-policy.yaml")
            Path(policy_path).write_text(policy)
        if policy_path:
            env["CLAUDE_DOCKER_EGRESS_POLICY"] = policy_path
        return subprocess.run(["bash", str(RUN_SH), "--api", ws],
                              env=env, capture_output=True, text=True, timeout=30)


class EgressPolicy(unittest.TestCase):
    def assert_refused(self, needle, **kw):
        r = run_api(**kw)
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn(needle, r.stderr)
        return r

    def test_unset_policy_refuses_even_the_gateway(self):
        self.assert_refused("'llm.example.eu' is not in CLAUDE_DOCKER_EGRESS_POLICY (unset)")

    def test_default_endpoint_is_not_implied(self):
        self.assert_refused("'api.anthropic.com' is not in", base_url=None)

    def test_gateway_missing_from_policy(self):
        self.assert_refused("'llm.example.eu' is not in",
                            policy="allow:\n  - pypi.org\n")

    def test_missing_file(self):
        self.assert_refused("is not a readable file", policy_path="/nonexistent/egress-policy.yaml")

    def test_injection_and_unsupported_yaml(self):
        for policy, needle in [
            ("allow:\n  - example.com http_access allow all\n", ":2: unsupported line"),
            ("allow:\n  - 'example.com'\n", "invalid egress-policy entry"),
            ("allow: [example.com]\n", ":1: unsupported line"),
            ("deny:\n  - example.com\n", ":1: unsupported line"),
            ("  - example.com\nallow:\n", ":1: unsupported line"),
            ("allow:\n\t- example.com\n", ":2: unsupported line"),
            ("allow:\n  - example.com#x\n", ":2: unsupported line"),
            ("---\nallow:\n", ":1: unsupported line"),
        ]:
            with self.subTest(policy=policy):
                self.assert_refused(needle, policy=policy)

    def test_valid_policy_passes(self):
        r = run_api(policy="# EU only\nallow:   # hosts\n  - llm.example.eu  # gateway\n"
                           "  - .pypi.org\n\n  - 10.20.0.0/16\r\n")
        self.assertIn("CLAUDE_DOCKER_RUNTIME must be", r.stderr)

    def test_suffix_entry_covers_gateway(self):
        r = run_api(policy="allow:\n  - .example.eu\n")
        self.assertIn("CLAUDE_DOCKER_RUNTIME must be", r.stderr)


if __name__ == "__main__":
    unittest.main()
