# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Schuberg Philis
"""--api locks model traffic to ANTHROPIC_BASE_URL; --report builds the PDF.

The endpoint checks run before container-runtime detection, so these cases
need no docker: an endpoint that passes stops at the invalid
CLAUDE_DOCKER_RUNTIME the helper sets. --report exits before that too.

Stdlib only, so CI's unit-test step keeps running with no install step.
"""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

RUN_SH = Path(__file__).resolve().parent.parent / "run.sh"


def run(args, **env_extra):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("ANTHROPIC_", "CLAUDE_DOCKER_"))}
    env.update(ANTHROPIC_AUTH_TOKEN="sk-test", CLAUDE_DOCKER_RUNTIME="none", **env_extra)
    with tempfile.TemporaryDirectory() as ws:
        return subprocess.run(["bash", str(RUN_SH), *args, ws],
                              env=env, capture_output=True, text=True, timeout=30)


class Endpoint(unittest.TestCase):
    def assert_refused(self, needle, **env):
        r = run(["--api"], **env)
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn(needle, r.stderr)

    def test_base_url_required(self):
        self.assert_refused("--api needs ANTHROPIC_BASE_URL")

    def test_provider_endpoint_refused(self):
        for url in ("https://api.anthropic.com", "https://x.claude.ai/v1", "https://claude.com"):
            with self.subTest(url=url):
                self.assert_refused("points at one", ANTHROPIC_BASE_URL=url)

    def test_injection_refused(self):
        self.assert_refused("is not a valid hostname",
                            ANTHROPIC_BASE_URL="https://a.eu\nhttp_access allow all/")
        self.assert_refused("is not a valid hostname", ANTHROPIC_BASE_URL="https://a b.eu/")

    def test_gateway_passes(self):
        for url in ("https://llm.example.eu/v1", "https://u:p@10.1.2.3:8443", "https://notanthropic.com"):
            with self.subTest(url=url):
                r = run(["--api"], ANTHROPIC_BASE_URL=url)
                self.assertIn("CLAUDE_DOCKER_RUNTIME must be", r.stderr)


LOG = """\
1790000000.100 900 172.18.0.3 TCP_TUNNEL/200 5000 CONNECT llm.example.eu:443 - HIER_DIRECT/10.9.8.7 -
1790000001.200 0 172.18.0.3 TCP_DENIED/403 3900 CONNECT api.anthropic.com:443 - HIER_NONE/- text/html
1790000002.300 300 172.18.0.3 TCP_TUNNEL/200 8000 CONNECT github.com:443 - HIER_DIRECT/140.82.121.4 -
"""
LEAK = "1790000003.000 50 172.18.0.3 TCP_TUNNEL/200 100 CONNECT statsig.anthropic.com:443 - HIER_DIRECT/1.2.3.4 -\n"


class Report(unittest.TestCase):
    def report(self, log):
        with tempfile.TemporaryDirectory() as state:
            d = Path(state, "claude-docker", "egress")
            d.mkdir(parents=True)
            (d / "20260927T100000Z-abc.log").write_text(log)
            (d / "20260927T100000Z-abc.meta").write_text("start=20260927T100000Z\nendpoint=llm.example.eu\n")
            out = Path(state, "r.pdf")
            r = run([f"--report={out}"], XDG_STATE_HOME=state)
            return r, out.read_bytes() if out.exists() else b""

    def test_pass(self):
        r, pdf = self.report(LOG)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(pdf.startswith(b"%PDF-1.4") and pdf.rstrip().endswith(b"%%EOF"))
        for needle in (b"Overall: PASS", b"llm.example.eu", b"TCP_DENIED", b"github.com", b"10.9.8.7"):
            self.assertIn(needle, pdf)

    def test_unrefused_provider_fails(self):
        r, pdf = self.report(LOG + LEAK)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn(b"Overall: FAIL", pdf)

    def test_no_logs(self):
        with tempfile.TemporaryDirectory() as state:
            r = run(["--report"], XDG_STATE_HOME=state)
        self.assertEqual(r.returncode, 1)
        self.assertIn("no session logs", r.stderr)


if __name__ == "__main__":
    unittest.main()
