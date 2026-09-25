#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Schuberg Philis
#
# egress.sh — smoke cell for the --api egress lock (openspec: api-egress-policy).
# Drives run.sh like smoke.sh does, but with the real docker (no shim): run.sh
# also starts the squid sidecar, the internal network and, with --gh, the gh
# sidecar, and this cell asserts on their teardown too. The in-container half
# is assert-in-container.sh with EXPECT_EGRESS=1.
#
# Usage: IMAGE=<tag> bash smoke/egress.sh [--gh]
#   --gh   also start the gh auth-proxy sidecar (fake token) and assert that
#          GitHub traffic flows agent → squid → gh sidecar → GitHub.
#
# Linux-only (util-linux `script` supplies the PTY that run.sh's `-it` needs).
set -euo pipefail

IMAGE="${IMAGE:-claude-code:local}"
WITH_GH=0
for arg in "$@"; do
  case "$arg" in
    --gh) WITH_GH=1 ;;
    *) echo "egress.sh: unknown argument '$arg'" >&2; exit 1 ;;
  esac
done

log() { echo "[egress-smoke] $*"; }
die() { echo "[egress-smoke] FAIL: $*" >&2; exit 1; }

REPO="$(cd "$(dirname "$0")/.." && pwd)"
# Under $HOME for the same reason as smoke.sh / run.sh: it is bind-mounted.
mkdir -p "$HOME/.cache/claude-docker"
TMPROOT=$(mktemp -d "$HOME/.cache/claude-docker/egress-smoke.XXXXXX")
trap 'rm -rf "$TMPROOT"' EXIT
WS="$TMPROOT/egress"
mkdir -p "$WS"
cp "$REPO/smoke/assert-in-container.sh" "$WS/assert-in-container.sh"
chmod +x "$WS/assert-in-container.sh"

# The fake gateway is example.com: it answers HTTPS, and the session never
# sends it a model request (CLAUDE_DOCKER_TEST_ENTRY replaces claude).
api_env=(CLAUDE_DOCKER_IMAGE="$IMAGE" ANTHROPIC_BASE_URL=https://example.com
         ANTHROPIC_AUTH_TOKEN=sk-fake-egress-smoke)
policy="$TMPROOT/egress-policy.yaml"

# 1. A policy line that tries to smuggle squid config is rejected before any
#    container resource exists.
printf 'allow:\n  - example.com\n  - example.com http_access allow all\n' >"$policy"
if out=$(env "${api_env[@]}" CLAUDE_DOCKER_EGRESS_POLICY="$policy" \
         bash "$REPO/run.sh" --api --ephemeral "$WS" </dev/null 2>&1); then
  die "run.sh accepted an injection attempt in egress-policy.yaml"
fi
printf '%s\n' "$out" | grep -q "egress-policy.yaml:3: unsupported line" \
  || die "injection attempt rejected without naming the line: $out"
log "PASS: invalid policy line aborts startup"

# 2. No policy: nothing is implied, not even the gateway, so run.sh refuses.
if out=$(env "${api_env[@]}" bash "$REPO/run.sh" --api --ephemeral "$WS" </dev/null 2>&1); then
  die "run.sh started an --api session without an egress policy"
fi
printf '%s\n' "$out" | grep -q "'example.com' is not in CLAUDE_DOCKER_EGRESS_POLICY" \
  || die "missing policy rejected without naming the gateway: $out"
log "PASS: --api without a policy aborts startup"

# 3. The session. localhost is listed so the rebinding check has a name that
#    is allowed but resolves inward.
cat >"$policy" <<'YAML'
# egress-smoke policy
allow:
  - example.com   # the fake gateway
  - localhost
YAML
if [ "$WITH_GH" = "1" ]; then
  printf '  - %s\n' github.com api.github.com uploads.github.com >>"$policy"
fi
entry="EXPECT_EGRESS=1 EXPECT_EGRESS_GH=$WITH_GH EXPECT_UID=$(id -u) EXPECT_GID=$(id -g) /workspaces/egress/assert-in-container.sh"
flags=(--api --ephemeral)
envs=("${api_env[@]}"
      CLAUDE_DOCKER_EGRESS_POLICY="$policy"
      CLAUDE_DOCKER_TEST_ENTRY="$entry")
if [ "$WITH_GH" = "1" ]; then
  flags+=(--gh)
  envs+=(GH_TOKEN=ghp_fakeEgressSmokeToken000000000000000000)
fi

rcfile="$TMPROOT/rc"
transcript="$TMPROOT/transcript.txt"
quoted="$(printf '%q ' env "${envs[@]}" bash "$REPO/run.sh" "${flags[@]}" "$WS"); echo \$? > $(printf '%q' "$rcfile")"
log "Cell: flags=${flags[*]} image=$IMAGE"
SHELL=/bin/bash timeout -k 10 300 script -qec "$quoted" "$transcript" >/dev/null 2>&1 || true
cat "$transcript"
rc=$(cat "$rcfile" 2>/dev/null || echo 124)
[ "$rc" = "0" ] || die "run.sh session exited $rc"
grep -q "RESULT: PASS" "$transcript" || die "in-container assertions did not report PASS"

# 4. Host-side: the startup banner, the end-of-session denied summary, and
#    teardown.
grep -q "egress proxy 'claude-egress-proxy-" "$transcript" \
  || die "run.sh did not announce the egress proxy"
grep -q "egress policy blocked:.*example.org.*CLAUDE_DOCKER_EGRESS_POLICY" "$transcript" \
  || die "end-of-session summary does not name example.org and CLAUDE_DOCKER_EGRESS_POLICY"
log "PASS: startup banner and denied-host summary"

leftover=$(docker ps -aq --filter "name=^claude-egress-" --filter "name=^claude-gh-"; \
           docker network ls -q --filter "name=^claude-egress-"; \
           docker network ls -q --filter "name=^claude-gh-")
[ -z "$leftover" ] || die "teardown left resources behind: $leftover"
log "PASS: no claude-egress-* / claude-gh-* resources left"

log "Cell PASS: flags=${flags[*]}"
