#!/usr/bin/env bash
set -euo pipefail
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
PR_NUMBER=$(gh pr view --json number -q .number)
STATE=$(gh pr view --json state -q .state)
TITLE=$(gh pr view --json title -q .title | sed 's/\\/\\\\/g; s/"/\\"/g')
HEAD_SHA=$(gh pr view --json headRefOid -q .headRefOid)
HEAD_BRANCH=$(git branch --show-current | sed 's/\\/\\\\/g; s/"/\\"/g')
echo "{\"repo\":\"$REPO\",\"pr\":$PR_NUMBER,\"state\":\"$STATE\",\"title\":\"$TITLE\",\"branch\":\"$HEAD_BRANCH\",\"sha\":\"$HEAD_SHA\"}"
