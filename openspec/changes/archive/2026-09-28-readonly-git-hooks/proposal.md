## Why

Workspaces are mounted read-write, and that includes `.git/hooks/`. Git runs
those hooks on the host at the next host-side `git commit`, `checkout`, `merge`
and so on — outside the container, as the user, with no capability drop. A
session that writes a hook there therefore reaches host code execution, which
the threat model's "host filesystem outside your passed workspaces is
protected" line does not warn about. The existing `.git/config` overlay already
keeps container writes away from the host's repo config; hooks are the other
half of the same surface.

## What Changes

- `run.sh` bind-mounts each main repo's `.git/hooks/` read-only over itself in
  the container. Existing hooks keep running in-container; nothing can be
  added, edited, or removed there.
- An absent `.git/hooks/` is created host-side first, so it is mounted too
  (rather than being creatable from inside, or created root-owned by the
  engine on Linux).
- A `.git/hooks` that is a symlink or not a directory is refused at startup
  with a clear error: the engine resolves a mount destination through a
  symlink, so the link itself would stay replaceable from inside.
- README Git worktrees and Threat model document the read-only hooks and the
  residual host-execution paths a writable workspace still has.
- `tests/git-hooks-ro.sh` checks the three cases via `run.sh`.

Not in scope: a `core.hooksPath` that points inside the worktree (e.g.
husky's `.husky/_`), `.envrc`, Makefiles, and editor task configs. They are
ordinary workspace files; protecting them would mean a read-only workspace,
which `--ro` already offers.

## Capabilities

### Modified Capabilities

- `multi-workspace-mounts`: adds a read-only `.git/hooks` requirement next to
  the existing `.git/config` overlay.

## Impact

`run.sh`, `README.md`, `tests/git-hooks-ro.sh`. A host repo with a symlinked
`.git/hooks` now fails to start with an actionable message.
