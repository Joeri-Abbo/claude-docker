# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Schuberg Philis
"""pins/az-requirements.txt must match pins/az.env and be fully hash-locked.

The Dockerfile installs az with --require-hashes from the lock, and sources no
version from az.env, so a hand-edited az.env or a lock regenerated for another
version would ship silently. update_pins.py writes both together.

Stdlib only, so CI's unit-test step keeps running with no install step.
"""

import re
import unittest
from pathlib import Path

PINS = Path(__file__).resolve().parent.parent / "pins"


class AzLock(unittest.TestCase):
    def setUp(self):
        env = (PINS / "az.env").read_text()
        self.version = re.search(r"^AZ_VERSION=(\S+)$", env, re.M).group(1)
        self.lock = (PINS / "az-requirements.txt").read_text()

    def test_core_matches_az_env(self):
        self.assertRegex(self.lock, rf"(?m)^azure-cli-core=={re.escape(self.version)} ")

    def test_every_requirement_is_hashed(self):
        # A requirement starts at column 0; its hashes are the continuation lines.
        blocks = re.split(r"(?m)^(?=[a-z0-9])", self.lock)
        reqs = [b for b in blocks if b and not b.startswith("#")]
        self.assertGreater(len(reqs), 1)
        for b in reqs:
            self.assertRegex(b, r"==\S+", b.splitlines()[0])
            self.assertIn("--hash=sha256:", b, b.splitlines()[0])


if __name__ == "__main__":
    unittest.main()
