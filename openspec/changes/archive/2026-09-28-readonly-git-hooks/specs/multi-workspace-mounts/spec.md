## ADDED Requirements

### Requirement: Repository hooks are read-only inside the container

For every workspace that receives the `.git/config` overlay, `run.sh` SHALL
bind-mount the host's `.git/hooks/` directory read-only over
`/workspaces/<name>/.git/hooks` in the container, because git runs those hooks
on the host and a container write there would be host code execution.
Existing hooks SHALL still run for git operations inside the container. When
`.git/hooks` is absent, `run.sh` SHALL create it host-side before mounting, so
it cannot be created from inside the container. When `.git/hooks` is a symlink
or not a directory, `run.sh` SHALL refuse to start with an error naming the
path, since a bind mount cannot protect a symlink entry.

#### Scenario: Hook write from the container fails

- **GIVEN** the user runs `claude-docker <repo>` and `<repo>/.git/hooks` is a directory
- **WHEN** a process inside the container creates, edits, or removes a file under `/workspaces/<repo>/.git/hooks`
- **THEN** the operation fails with a read-only error
- **AND** `<repo>/.git/hooks` on the host is unchanged after the container exits

#### Scenario: Existing hook still runs inside the container

- **GIVEN** `<repo>/.git/hooks/post-commit` is an executable hook on the host
- **WHEN** `git commit` runs inside the container
- **THEN** the hook runs

#### Scenario: Absent hooks directory cannot be created from inside

- **GIVEN** `<repo>/.git/hooks` does not exist on the host
- **WHEN** the user runs `claude-docker <repo>`
- **THEN** `<repo>/.git/hooks` exists on the host as an empty directory owned by the user
- **AND** creating a file under `/workspaces/<repo>/.git/hooks` inside the container fails

#### Scenario: Symlinked hooks directory is refused

- **GIVEN** `<repo>/.git/hooks` is a symlink
- **WHEN** the user runs `claude-docker <repo>`
- **THEN** `run.sh` exits non-zero before starting any container, naming the path
