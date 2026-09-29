## 1. Spec

- [x] 1.1 Proposal: the `/repositories/{id}` alias bypasses the default repo-deletion block
- [x] 1.2 Spec delta: `gh-auth-proxy` "Request filtering policy" names both routes and gains an alias scenario

## 2. Implementation

- [x] 2.1 `run.sh`: widen `@gh_proxy_repo_delete` to `^/(repos/[^/]+/[^/]+|repositories/[0-9]+)/?$` (one regex — no reliance on how Caddy merges repeated matchers)
- [x] 2.2 README "Filtering and policy": mention the alias

## 3. Verification

- [x] 3.1 `tests/gh-proxy-integration.sh`: `DELETE /repositories/123` is answered `403` with the policy body and never reaches the mock upstream
- [x] 3.2 `shellcheck` clean
- [x] 3.3 `openspec validate gh-proxy-block-repo-id-delete --strict` passes
