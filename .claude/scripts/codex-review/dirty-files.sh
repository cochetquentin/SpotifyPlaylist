#!/usr/bin/env bash
# Outputs JSON {dirty: [...], new: [...]} of working tree state before corrections.
# Uses NUL-delimited git output to handle paths containing spaces correctly.
# Rename/copy entries (R/C) emit two NUL-delimited records; the second (old path) is skipped.
set -euo pipefail

DIRTY_JSON="["
NEW_JSON="["
DIRTY_FIRST=true
NEW_FIRST=true
SKIP_NEXT=false

while IFS= read -r -d $'\0' entry; do
  [[ -z "$entry" ]] && continue

  if $SKIP_NEXT; then
    SKIP_NEXT=false
    continue
  fi

  status="${entry:0:2}"
  path="${entry:3}"
  escaped=$(printf '%s' "$path" | sed 's/\\/\\\\/g; s/"/\\"/g')

  # Rename or copy: next NUL record is the old path — skip it
  if [[ "${status:0:1}" == "R" || "${status:0:1}" == "C" ]]; then
    SKIP_NEXT=true
  fi

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
