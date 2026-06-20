#!/usr/bin/env bash
# Usage: anti-loop-check.sh <REPO> <PR>
# exit 0 + "T_TRIGGER=<iso>" on stdout → proceed
# exit 1 + reason on stdout → STOP
# ISO 8601 UTC strings are lexicographically comparable — no date conversion needed
set -euo pipefail
REPO=$1
PR=$2

T_TRIGGER=$(gh api --paginate "repos/$REPO/issues/$PR/comments" \
  --jq '.[] | select(.body | ltrimstr("\n") | rtrimstr("\n") | ltrimstr("\r") | rtrimstr("\r") | ascii_downcase | . == "@codex review") | .created_at' | tail -1)

T_CODEX_R=$(gh api --paginate "repos/$REPO/pulls/$PR/reviews" \
  --jq '.[] | select(.user.login == "chatgpt-codex-connector[bot]") | .submitted_at' | tail -1 || true)
T_CODEX_C=$(gh api --paginate "repos/$REPO/pulls/$PR/comments" \
  --jq '.[] | select(.user.login == "chatgpt-codex-connector[bot]") | .created_at' | tail -1 || true)
T_CODEX_I=$(gh api --paginate "repos/$REPO/issues/$PR/comments" \
  --jq '.[] | select(.user.login == "chatgpt-codex-connector[bot]") | .created_at' | tail -1 || true)

HEAD_SHA=$(gh pr view --json headRefOid -q .headRefOid)
T_COMMIT=$(gh api "repos/$REPO/commits/$HEAD_SHA" --jq '.commit.committer.date' 2>/dev/null \
  || date -u -d "$(git log -1 --format="%cI")" "+%Y-%m-%dT%H:%M:%SZ")

# Max of T_CODEX_{R,C,I} via string comparison (ISO 8601 UTC is lexicographically ordered)
T_CODEX_MAX=""
for t in "$T_CODEX_R" "$T_CODEX_C" "$T_CODEX_I"; do
  [[ -n "$t" && "$t" > "$T_CODEX_MAX" ]] && T_CODEX_MAX="$t"
done

# Anti-loop: @Codex review already posted after last commit and Codex hasn't responded yet
if [[ -n "$T_TRIGGER" && "$T_TRIGGER" > "$T_COMMIT" && "$T_CODEX_MAX" < "$T_TRIGGER" ]]; then
  echo "Anti-boucle : @Codex review déjà posté après le dernier commit et Codex n'a pas encore répondu."
  exit 1
fi

echo "T_TRIGGER=$T_TRIGGER"