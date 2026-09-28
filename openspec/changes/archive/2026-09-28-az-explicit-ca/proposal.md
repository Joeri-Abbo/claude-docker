## Why

Review of #105: `--az` installed the file named by the host's
`REQUESTS_CA_BUNDLE` into the container's system trust store. Many hosts set
that variable for unrelated reasons, so `--az` could silently trust a CA
system-wide that the user never meant for it.

## What Changes

- The `--az` private CA comes from an explicit `CLAUDE_DOCKER_AZ_CA`, like
  `CLAUDE_DOCKER_API_CA` under `--api`. The host `REQUESTS_CA_BUNDLE` is no
  longer read.
- `--help` lists `CLAUDE_DOCKER_AZ_CA`; README says it is trusted for all TLS
  in the container.

## Impact

- Specs: `external-cli-tools` (Credentials opt-in), `cli-help` (Help output
  enumerates every wrapper flag), both MODIFIED.
- Code: `run.sh`, `README.md`, `tests/test_az_ca.py`.

The CLI refuses to drop a scenario from a MODIFIED requirement, so the two
existing CA scenarios keep their `REQUESTS_CA_BUNDLE` titles while their steps
now use `CLAUDE_DOCKER_AZ_CA`.
