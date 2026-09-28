#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Schuberg Philis
#
# run.sh-driven check that every mounted repo's .git/hooks is read-only inside
# the container: an existing hook still runs, but nothing can be added, for a
# regular hooks dir and an absent one. A symlinked hooks dir is refused.
#
# Usage: IMAGE=claude-code:local bash tests/git-hooks-ro.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# Under $HOME, not /tmp: Colima only shares $HOME into its VM by default.
mkdir -p "$HOME/.cache"
SCRATCH="$(mktemp -d "$HOME/.cache/claude-docker-hooks-test.XXXXXX")"
trap 'rm -rf "$SCRATCH"' EXIT
export CLAUDE_DOCKER_IMAGE="${IMAGE:-claude-code:local}"

mkrepo() { git init -q "$SCRATCH/$1"; }
mkrepo hooks-plain
mkrepo hooks-absent
mkrepo hooks-symlink
# shellcheck disable=SC2016  # $(...) is meant for the hook, not this shell
printf '#!/bin/sh\ntouch "$(git rev-parse --show-toplevel)/hook-ran"\n' >"$SCRATCH/hooks-plain/.git/hooks/post-commit"
chmod +x "$SCRATCH/hooks-plain/.git/hooks/post-commit"
rm -rf "$SCRATCH/hooks-absent/.git/hooks"
mkdir "$SCRATCH/shared-hooks"
rm -rf "$SCRATCH/hooks-symlink/.git/hooks"
ln -s "$SCRATCH/shared-hooks" "$SCRATCH/hooks-symlink/.git/hooks"

results="$SCRATCH/hooks-plain/results"
: >"$results"

# Symlinked hooks dir: refused before any container starts.
if CLAUDE_DOCKER_TEST_ENTRY=true bash "$ROOT/run.sh" --ephemeral "$SCRATCH/hooks-symlink" </dev/null >/dev/null 2>"$SCRATCH/err"; then
  echo "FAIL: symlinked .git/hooks was not refused" >>"$results"
elif grep -q 'symlink or not a directory' "$SCRATCH/err"; then
  echo "PASS: symlinked .git/hooks is refused" >>"$results"
else
  echo "FAIL: run.sh failed for another reason: $(cat "$SCRATCH/err")" >>"$results"
fi

cat >"$SCRATCH/hooks-plain/assert.sh" <<'EOF'
out=/workspaces/hooks-plain/results
for r in hooks-plain hooks-absent; do
  h="/workspaces/$r/.git/hooks"
  # Every way in: write into it, or replace it with a fresh dir.
  if touch "$h/pre-commit" 2>/dev/null \
     || { rm -rf "$h" 2>/dev/null; mkdir "$h" 2>/dev/null && touch "$h/pre-commit"; }; then
    echo "FAIL: $r: .git/hooks is writable" >>"$out"
  else
    echo "PASS: $r: .git/hooks is read-only" >>"$out"
  fi
done
cd /workspaces/hooks-plain
# safe.directory: Docker Desktop file sharing intermittently reports the
# workspace as root-owned (also on main) — unrelated to what this checks.
git -c safe.directory='*' -c user.name=t -c user.email=t@example.com commit -q --allow-empty -m t >>"$out" 2>&1
if [ -f hook-ran ]; then echo "PASS: existing hook runs" >>"$out"; else echo "FAIL: existing hook did not run" >>"$out"; fi
EOF

# run.sh passes -it, so it needs a TTY: wrap it in script(1).
cmd=(env CLAUDE_DOCKER_TEST_ENTRY="exec sh /workspaces/hooks-plain/assert.sh"
  bash "$ROOT/run.sh" --ephemeral "$SCRATCH/hooks-plain" "$SCRATCH/hooks-absent")
if script --version 2>/dev/null | grep -q util-linux; then
  script -qec "$(printf '%q ' "${cmd[@]}")" /dev/null </dev/null >/dev/null
else
  script -q /dev/null "${cmd[@]}" </dev/null >/dev/null
fi

grep -q 'existing hook' "$results" || echo "FAIL: container produced no results" >>"$results"
# Host-side: the absent dir was created, and no hooks dir gained a file.
if [ -d "$SCRATCH/hooks-absent/.git/hooks" ]; then echo "PASS: absent hooks dir created host-side"; else echo "FAIL: absent hooks dir not created"; fi >>"$results"
if [ -z "$(ls -A "$SCRATCH/hooks-absent/.git/hooks" 2>/dev/null)" ] \
   && [ ! -e "$SCRATCH/hooks-plain/.git/hooks/pre-commit" ]; then
  echo "PASS: no hook written on the host"
else
  echo "FAIL: a hook was written on the host"
fi >>"$results"
cat "$results"
! grep -q '^FAIL' "$results"
