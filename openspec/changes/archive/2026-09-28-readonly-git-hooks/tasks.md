## 1. Implementation

- [x] 1.1 `run.sh`: in the per-workspace `.git/config` overlay loop, create an absent `.git/hooks` host-side and bind-mount it `:ro` over itself
- [x] 1.2 `run.sh`: refuse a symlinked or non-directory `.git/hooks` with an actionable error
- [x] 1.3 Comment the residual `core.hooksPath`-inside-worktree gap at the mount

## 2. Documentation

- [x] 2.1 README Git worktrees: `.git/hooks` is read-only in-container
- [x] 2.2 README Threat model: writable workspaces still reach host execution through repo files the host runs

## 3. Verification

- [x] 3.1 `tests/git-hooks-ro.sh`: plain and absent hooks dirs are read-only, an existing hook still runs, nothing lands on the host, a symlinked dir is refused
- [x] 3.2 The same test fails against the previous `run.sh`
- [x] 3.3 `shellcheck run.sh entrypoint.sh smoke/*.sh tests/git-hooks-ro.sh` clean at CI severity
- [x] 3.4 `openspec validate readonly-git-hooks --strict` passes
