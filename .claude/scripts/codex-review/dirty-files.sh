#!/usr/bin/env bash
# Outputs JSON {dirty: [...], new: [...]} of working tree state before corrections.
# Uses NUL-delimited git output to handle paths containing spaces correctly.
set -euo pipefail

DIRTY_JSON="["
NEW_JSON="["
DIRTY_FIRST=true
NEW_FIRST=true

while IFS= read -r -d $'\0' entry; do
  [[ -z "$entry" ]] && continue
  status="${entry:0:2}"
  path="${entry:3}"
  escaped=$(printf '%s' "$path" | sed 's/\\/\\\\/g; s/"/\\"/g')

  if [[ "$status" == "??" ]]; then
    $NEW_FIRST || NEW_JSON+=","
    NEW_JSON+="\"$escaped\""
    NEW_FIRST=false
  else
    $DIRTY_FIRST || DIRTY_JSON+=","
    DIRTY_JSON+="\"$escaped\""
    DIRTY_FIRST=false
  fi
done < <(git status --porcelain -z || true)

DIRTY_JSON+="]"
NEW_JSON+="]"

echo "{\"dirty\":$DIRTY_JSON,\"new\":$NEW_JSON}"