## Why

The gh-proxy sidecar's default policy blocks repository deletion by matching
`DELETE ^/repos/[^/]+/[^/]+/?$` on `api.github.com`. GitHub also serves every
repository route under the numeric-id alias `/repositories/{id}` — the form its
own pagination `Link` headers use — so a compromised session can look up the id
(`gh api repos/o/r --jq .id`) and send `DELETE /repositories/<id>` through the
sidecar, sidestepping the one destructive call the policy exists to stop.

## What Changes

- Widen the default `@gh_proxy_repo_delete` matcher in `run.sh` to a single
  alternation, `^/(repos/[^/]+/[^/]+|repositories/[0-9]+)/?$`, so both routes
  answer `403` with the existing policy body and never reach GitHub.
- Extend `tests/gh-proxy-integration.sh` to assert the alias is blocked and
  never reaches the mock upstream.
- Mention the alias in README's "Filtering and policy" paragraph.

Not in scope: other destructive endpoints, and case-variant paths
(`/REPOS/...`) — whether GitHub routes those is unverified, so they are not
guessed at here.

## Capabilities

### Modified Capabilities

- `gh-auth-proxy`: the default request-filtering policy covers the
  `/repositories/{id}` alias of repository deletion.

## Impact

- `run.sh` (generated Caddyfile), `tests/gh-proxy-integration.sh`, `README.md`.
- No change for requests that passed before, other than `DELETE
  /repositories/{id}`, which is now refused.
