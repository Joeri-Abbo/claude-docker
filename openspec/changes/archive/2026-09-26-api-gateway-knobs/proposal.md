## Why

Gateway setups (LiteLLM routing to `azure/…` or `aws/…` model IDs) need two more
Claude Code variables that `--api` does not forward:

- `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS`: gateways to non-Anthropic models
  often reject the experimental `anthropic-beta` headers.
- `CLAUDE_CODE_MAX_CONTEXT_TOKENS`: gateway model IDs are unknown to Claude
  Code, so it cannot infer their context window and auto-compact holds the
  session to a conservative default.

Neither is a secret. Privacy switches (`CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`,
`DISABLE_TELEMETRY`, …) are deliberately left out: they are not gateway config,
and `settings.docker.json`'s `env` block already covers them.

## What Changes

- `run.sh` forwards both variables by bare name under `--api`; `--help` and
  README list them, and README points privacy switches at `settings.docker.json`.

## Impact

- Specs: `external-cli-tools` (Custom model endpoint opt-in, MODIFIED).
- Code: `run.sh`, `README.md`.
