## 1. Spec

- [x] 1.1 Proposal: why following symlinks in the overlay step breaks the host-filesystem guarantee
- [x] 1.2 Spec delta: the `multi-workspace-mounts` overlay requirement refuses symbolic links, with a scenario

## 2. Implementation

- [x] 2.1 `run.sh`: overlay only when `.git` is a directory that is not a symlink, and `.git/config` is a regular file that is not a symlink
- [x] 2.2 README "Git worktrees": note that a symlinked `.git` or `.git/config` is skipped

## 3. Verification

- [x] 3.1 `tests/test_git_config_overlay.py`: real `run.sh` against a stub runtime. Overlay present for a real repo, absent for a symlinked `.git` and a symlinked `.git/config`. Fails on the pre-fix `run.sh`
- [x] 3.2 `shellcheck run.sh entrypoint.sh smoke/*.sh` clean
- [x] 3.3 `openspec validate refuse-symlinked-git-config --strict` passes
