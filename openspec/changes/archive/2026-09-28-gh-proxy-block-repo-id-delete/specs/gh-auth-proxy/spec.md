## MODIFIED Requirements

### Requirement: Request filtering policy

The sidecar SHALL enforce request policy before forwarding. The default policy SHALL block repository deletion — `DELETE` requests matching `^/(repos/[^/]+/[^/]+|repositories/[0-9]+)/?$` on `api.github.com`, i.e. both `/repos/{owner}/{repo}` and its numeric-id alias `/repositories/{id}` — with a `403` response whose body identifies the claude-docker proxy policy. All other requests SHALL pass. Users SHALL be able to extend policy by pointing `CLAUDE_DOCKER_GH_POLICY` at a Caddyfile snippet that is imported into the generated sidecar config. Policy configuration SHALL NOT be readable or writable from inside the agent container.

#### Scenario: Repo deletion is blocked by default

- **WHEN** `gh api -X DELETE /repos/someorg/somerepo` runs inside the agent container
- **THEN** the response is `403` with a body identifying the claude-docker gh-proxy policy
- **AND** the request never reaches GitHub

#### Scenario: Repo deletion by numeric id is blocked by default

- **WHEN** `gh api -X DELETE /repositories/123456` runs inside the agent container
- **THEN** the response is `403` with a body identifying the claude-docker gh-proxy policy
- **AND** the request never reaches GitHub

#### Scenario: Non-destructive requests pass

- **WHEN** `gh pr list` and `gh api /rate_limit` run inside the agent container
- **THEN** both succeed

#### Scenario: User-supplied policy extension is honoured

- **GIVEN** `CLAUDE_DOCKER_GH_POLICY` points to a snippet blocking `DELETE` on `^/repos/[^/]+/[^/]+/git/refs/.*`
- **WHEN** a matching request is made from the agent container
- **THEN** it is answered `403` by the sidecar
