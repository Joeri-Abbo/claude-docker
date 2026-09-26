## Why

Review of #105 (stefanwb):

1. `python-dateutil msrest azure-common` and `azure-cli-core`'s transitive deps
   resolved fresh on every build, so the az layer was not reproducible.
2. `--az` mounted `~/.azure/azureProfile.json` and `clouds.config`. With PAT
   auth and no token cache they enable nothing, yet carry tenant and
   subscription IDs and the account name into the container.
3. Telemetry upload was skipped only because the wrapper bypasses
   azure-cli's `__main__`.

## What Changes

- `update_pins.py` writes a hash-locked `pins/az-requirements.txt` with
  `pins/az.env`; the Dockerfile installs from it with `--require-hashes` and
  fails if it doesn't pin the `az.env` version. `tests/test_az_lock.py` checks
  the same.
- `--az` mounts no host `~/.azure` file; the smoke sentinel moves to the PAT.
- The `az` wrapper sets `AZURE_CORE_COLLECT_TELEMETRY=no`.
- Docs: README pinning and `--az` text, `.trivyignore` scope note, design doc
  PAT pointer (`op run` instead of the closed #73).

## Impact

- Specs: `external-cli-tools` (Credentials opt-in, az requirement),
  `version-pin-refresh` (fragments) — MODIFIED.
- Code: `update_pins.py`, `pins/az-requirements.txt`, `Dockerfile`, `run.sh`,
  smoke, `.github/workflows/docker.yml`, `.trivyignore`, `README.md`, tests.

Note: the scenario "--az mounts only the non-secret az config" keeps its name
(this OpenSpec version refuses to drop a scenario from a MODIFIED requirement);
its steps now assert that no host `~/.azure` file is mounted.
