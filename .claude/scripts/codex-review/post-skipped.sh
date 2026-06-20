#!/usr/bin/env bash
# Usage: bash post-skipped.sh <PR> << 'EOF'
#   markdown table body
# EOF
# Posts a GitHub comment with the skipped corrections table.
# Does nothing if stdin is empty.
set -euo pipefail
PR=$1
BODY=$(cat)

[[ -z "$BODY" ]] && exit 0

gh pr comment "$PR" --body "$BODY"