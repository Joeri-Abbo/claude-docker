## 1. Spec & design

- [x] 1.1 Proposal: why the deferred `automate-version-pins` 8.2 item becomes its own change, what ships, and the sequencing against the unarchived `automate-version-pins` delta
- [x] 1.2 Design: single long-lived branch, `python3` over `uv run`, the token choice and its approval-gated CI, dispatch inputs through `env`, absolute link in the PR body
- [x] 1.3 Spec delta: `version-pin-refresh` gains `Scheduled unattended refresh` with the changed-pins and unchanged-pins paths, PR replacement, on-demand overrides, failed-run and manual-pin scenarios

## 2. Workflow

- [x] 2.1 `.github/workflows/pins-updater.yml`: Monday `schedule` offset from Dependabot's window, plus `workflow_dispatch` with `soak` and `block-major-bumps` inputs
- [x] 2.2 Top-level `permissions: contents: read` with a job-level `contents: write` + `pull-requests: write` scope; `concurrency: pins-updater` with `cancel-in-progress: false`
- [x] 2.3 `checkout` with `persist-credentials: false`, and an explicit push URL so the push authenticates with the token it means to use
- [x] 2.4 Run `python3 update_pins.py` on the runner's preinstalled interpreter — no toolchain install step, matching how `ci.yml` already invokes the script; `tee` the report so it lands in both the job log and the PR body
- [x] 2.5 Dispatch inputs bound to `env` and read as shell variables, never interpolated into a `run:` body; `inputs.soak || '7'` covers the schedule trigger and a cleared field
- [x] 2.6 Detect pin changes with `git status --porcelain -- pins`; on no change, write the outcome to the step summary and open nothing
- [x] 2.7 On change: commit, force-push `bump/pins`, then `gh pr edit` the open PR if one exists, otherwise `gh pr create`
- [x] 2.8 PR body: intro line linking the workflow by absolute URL, a pointer at the `⚠ needs your eyes` manual pins, and the full report inside a `<details>` fenced block
- [x] 2.9 Use `secrets.GITHUB_TOKEN`, and state in the workflow comment that the PR's CI runs wait for a maintainer's _Approve and run_

## 3. Documentation

- [x] 3.1 README "Updating pinned tool versions": the unattended path, the single-branch rationale, and how the workflow invokes the script
- [x] 3.2 README callout: the PR's required checks report only after a maintainer clicks _Approve and run_
- [x] 3.3 Tick `automate-version-pins` task 8.2, pointing at this change

## 4. Verification

- [x] 4.1 YAML parses; `yamllint` clean apart from the SHA-comment spacing warning every existing workflow here shares; every `run:` block passes `bash -n`
- [x] 4.2 `zizmor` clean — no template-injection sink, no over-broad `permissions`, no unpinned action
- [x] 4.3 Confirm by inspection that the generated commit and PR body satisfy this repo's own PR gates (`lint-git`, `mcvs-pr-validation-action`)
- [x] 4.4 `openspec validate schedule-pin-refresh --strict` passes
- [x] 4.5 ~~Create a `PINS_UPDATER_TOKEN` repo secret~~ — dropped: `GITHUB_TOKEN` PRs get their `pull_request` runs after _Approve and run_ (see #70), so no long-lived PAT is needed
- [x] 4.6 Confirm the changed-pins path end to end: branch pushed, PR opened with the full report, and this repo's PR checks running on it once approved — #70 (2026-09-21)
- [x] 4.7 Confirm the unchanged-pins path opens nothing — by inspection: on an empty `git status --porcelain -- pins` the detect step sets `changed=false`, writes the step summary, and the PR step's `if:` skips it. Every scheduled and dispatched run so far (through 2026-09-27) found changes, so no run has taken this path yet
