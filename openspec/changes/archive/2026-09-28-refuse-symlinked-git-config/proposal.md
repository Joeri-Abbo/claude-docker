## Why

`run.sh` builds the container-only `.git/config` overlay on the host. It tests
`<ws>/.git/config` with `[ -f ]` and copies it with `cp`, and both follow
symbolic links. The workspace is writable from inside the container. So a link
that an earlier session leaves at `.git` or `.git/config` makes a later launch
copy a host file into the container, even when that file is outside every
passed workspace. This breaks the threat model's promise: "Protected: host
filesystem outside your passed workspaces".

## What Changes

- The overlay is created only when `<ws>/.git` is a real directory and
  `<ws>/.git/config` is a regular file, and neither one is a symbolic link.
  Otherwise the workspace is mounted without the overlay, the same as a
  non-git directory.
- A unit test runs the real `run.sh` against a stub runtime. It checks that the
  overlay is mounted for a real repo and skipped for both link cases.
- The README "Git worktrees" section says that a symlinked `.git` or
  `.git/config` is skipped.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `multi-workspace-mounts`: the overlay requirement gains a rule that symbolic
  links are never followed, plus a scenario for it.

## Impact

- `run.sh`: one condition in the overlay loop.
- `tests/test_git_config_overlay.py`: new stdlib unit test, picked up by CI's
  existing `unittest discover` step.
- `README.md`: one sentence.
- A repo whose `.git` is deliberately a symlink to its git dir loses the
  relative-worktrees overlay. It falls back to `git worktree repair`, which is
  what worktrees mounted standalone already use.
