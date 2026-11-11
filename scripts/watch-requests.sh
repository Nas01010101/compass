#!/usr/bin/env bash
# Owner side: polls the repo for new Request issues and open PRs, prints the first
# new ones and exits, so the caller (a person or an agent session) handles them and restarts it.
set -euo pipefail
REPO="${REPO:-Nas01010101/compass}"
SEEN="${SEEN:-${TMPDIR:-/tmp}/compass-seen.txt}"
touch "$SEEN"
while true; do
  new=$( { gh issue list -R "$REPO" --label request --state open --json number,title,author \
             --jq '.[] | "issue #\(.number) \(.author.login): \(.title)"'
           gh pr list -R "$REPO" --state open --json number,title,author \
             --jq '.[] | "pr #\(.number) \(.author.login): \(.title)"'; } | grep -vxFf "$SEEN" || true)
  if [ -n "$new" ]; then
    echo "$new" | tee -a "$SEEN"
    # Desktop ping for the owner when the harness notifier exists; harmless elsewhere.
    [ -x "$HOME/.claude/notify.sh" ] && "$HOME/.claude/notify.sh" "Compass request" "$(echo "$new" | head -1)" || true
    exit 0
  fi
  sleep "${INTERVAL:-60}"
done
