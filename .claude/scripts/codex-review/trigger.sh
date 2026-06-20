#!/usr/bin/env bash
# Usage: trigger.sh <PR>
# Posts @Codex review to trigger a new Codex review cycle.
# Review focus is governed by .github/copilot-instructions.md
set -euo pipefail
PR=$1
gh pr comment "$PR" --body "@Codex review"