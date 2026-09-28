## Context

`update_pins.py` is already a complete unattended actor: it takes no interactive
input, it exits non-zero on any resolve/download/integrity failure, and it
swaps fragments in via `os.replace` only on full success, so a failed run leaves
`pins/` byte-identical. What is missing is a caller and a delivery mechanism for
its output.

The delivery mechanism matters more than the caller. A pin bump is not reviewable
by reading the diff — the diff is a version string and two sha256s, and the
question a reviewer actually has is "does the image still build and do the tools
still run". That question is answered by this repo's existing PR checks, so the
design goal is: get the refresh into a pull request that those checks run on.

Constraints observed in the repo:

- `main protection` requires the `Validate` and `Docker build (validate, no
  push)` contexts, and sets `dismiss_stale_reviews_on_push: true`.
- `ci.yml` already invokes the script twice as `python3 update_pins.py`
  (`--audit`, `--list-npm-tools`) on the runner's preinstalled interpreter.
- The script declares `requires-python = ">=3.11"` and `dependencies = []`.
- `mcvs-general-action`'s commitlint config disables `body-max-line-length`, so
  a generated commit body longer than 100 characters passes `lint-git`.

## Goals / Non-Goals

**Goals:**

- A refresh happens every week whether or not anyone remembers.
- Its output lands where the image actually gets built and smoke-tested.
- Exactly one pins PR exists at any time, always showing the newest resolution.
- An operator can run it on demand with a different soak or major-bump policy.
- The workflow is a thin caller: no resolution, selection, or hashing logic
  moves into YAML, where it would drift from the script and be untestable.

**Non-Goals:**

- Auto-merging a green pins PR.
- Touching the manual pins (`nodejs`, `task`, `go`, base digest).
- Reimplementing the report. The script's stdout *is* the PR body.

## Decisions

### One long-lived branch, force-pushed — not a dated branch per run

A dated branch per run accumulates PRs that each propose a strictly worse
answer than the newest one: the pins in last month's PR have been superseded,
and merging it would immediately be reverted by the next refresh. So the branch
is `bump/pins`, rebuilt from `main` and force-pushed every run, and the workflow
edits the open PR in place when one exists.

*Cost:* `dismiss_stale_reviews_on_push` means an approved-but-unmerged pins PR
loses its approval on the next Monday. That is the correct outcome — the thing
that was approved is gone — but it does mean a pins PR should be merged the week
it appears.

*Known gap, deliberately not solved:* the push is unconditional, so a week whose
resolution happens to be byte-identical to the open PR's tree still produces a
new commit SHA and dismisses the review. Guarding on `HEAD^{tree}` against the
remote branch would fix it; it is not worth the extra fetch until it is observed
to happen, since `claude-code` alone moves often enough that most weeks differ.

### `python3`, not `uv run`

The operator-facing command in README is `uv run update_pins.py`, because the
image ships `uv`. On a runner it would mean bootstrapping `uv` first — an extra
step that can fail before any work happens, and one more thing to keep pinned —
to resolve a dependency set that is empty. The runner's python3.12 already
satisfies `requires-python`, and `ci.yml` already calls the script this way. So
the workflow calls `python3` directly and the workflow has no install step at
all.

### `GITHUB_TOKEN`, with CI gated on approval

The PR is opened with the job's `GITHUB_TOKEN`. GitHub still creates the PR's
`pull_request` runs, but holds them until a maintainer clicks _Approve and run_.
This was confirmed on the scheduled PRs of 2026-08-31, 2026-09-07 and #70. That
is enough: a human reviews every bump anyway, and approving CI is part of that
review. A fine-grained PAT (`PINS_UPDATER_TOKEN`) would skip the click, but it
adds a long-lived secret to rotate and guard for no real gain, so it was
dropped.

`checkout` runs with `persist-credentials: false`, and the push names its
remote URL explicitly, so the only write credential in use is the one the push
step passes.

### Dispatch inputs reach the script through `env`

`inputs.soak` and `inputs.block-major-bumps` are attacker-influenced in the
general case and are never interpolated into a `run:` body, which would be a
template-injection sink. They are bound to `env:` and read as `"$SOAK"` /
`"$BLOCK_MAJOR"`. `inputs.soak || '7'` covers both the schedule trigger, where
inputs are absent, and a dispatcher who clears the field.

### Absolute URL in the generated PR body

GitHub rewrites repo-relative markdown links only when rendering a file from the
repo — not in an issue or PR body, where the browser resolves them against
`/<org>/<repo>/pull/`. The body therefore builds the workflow link from
`${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/blob/main/…`. The README link to the
same file stays relative, because that one *is* rendered from a repo file.

## Risks / Trade-offs

- **An unapproved PR sits idle.** If no one approves its runs, the required
  checks never report and the PR can't merge (#67 closed that way). This is
  acceptable: the next Monday's run replaces it.
- **`concurrency: pins-updater` with `cancel-in-progress: false`.** Two runs
  force-pushing the same branch would race; cancelling a run mid-push could
  leave the branch and the PR body describing different resolutions. Serializing
  and never cancelling costs nothing at a weekly cadence.
- **The report is dumped verbatim into the PR body.** It is the script's own
  output, wrapped in `<details>` and a fenced block, so a pathological report
  cannot break out of the fence into markdown — but a very long one would make
  for a long body. Acceptable: the report is bounded by the number of pinned
  tools.
