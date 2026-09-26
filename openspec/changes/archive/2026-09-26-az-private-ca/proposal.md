## Why

An on-prem Azure DevOps Server typically serves TLS from an internal CA. On the
host, users point az at it with `REQUESTS_CA_BUNDLE=~/.azure/tfs-ca.pem`. In
the container that host path does not exist, `requests` falls back to certifi,
and `git` to the same server needs the CA as well, so `--az` fails at the first
TLS handshake against such a server.

## What Changes

- Under `--az`, the file the host's `REQUESTS_CA_BUNDLE` names is mounted
  read-only as `claude-docker-az.crt` and installed by the entrypoint's existing
  `update-ca-certificates` step, so az, git and curl trust it. The host path is
  not forwarded; a set path that is not a file is a startup error.
- The `az` wrapper defaults `REQUESTS_CA_BUNDLE` to the system bundle.
- `--help`, README (`--az` row, a private-CA section, threat model) and
  `tests/test_az_ca.py`.

## Impact

- Specs: `external-cli-tools` (Credentials opt-in, MODIFIED).
- Code: `run.sh`, `Dockerfile`, `README.md`, `tests/test_az_ca.py`.
