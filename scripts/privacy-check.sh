#!/bin/bash
#
# Pre-push privacy check. Run from anywhere; it finds the repo root itself.
# Fails (non-zero exit) if anything that looks like private user data,
# secrets, or personal identifiers is TRACKED in git. Checks the working
# tree's tracked file list, not just git status, so it also catches files
# that were tracked in an earlier commit and never removed.
#
# This is a first line of defence, not a substitute for reading
# `git status` / `git diff` yourself before pushing.
set -uo pipefail

cd "$(git rev-parse --show-toplevel)" || exit 1
FAIL=0

fail() { echo "FAIL: $1"; FAIL=1; }
ok()   { echo "ok:   $1"; }

TRACKED=$(git ls-files)

# 1. .env files (anything but .env.example)
BAD_ENV=$(echo "$TRACKED" | grep -E '(^|/)\.env(\..*)?$' | grep -v '\.env\.example$')
[ -n "$BAD_ENV" ] && fail "tracked .env file(s):\n$BAD_ENV" || ok "no tracked .env files"

# 2. Databases
BAD_DB=$(echo "$TRACKED" | grep -iE '\.(db|sqlite|sqlite3)$')
[ -n "$BAD_DB" ] && fail "tracked database file(s):\n$BAD_DB" || ok "no tracked database files"

# 3. Personal documents (PDF/DOCX) - none are expected to be tracked at all
BAD_DOCS=$(echo "$TRACKED" | grep -iE '\.(pdf|docx)$')
[ -n "$BAD_DOCS" ] && fail "tracked PDF/DOCX file(s) - confirm these are intentional, sanitised examples:\n$BAD_DOCS" || ok "no tracked PDF/DOCX files"

# 4. data/ must contain nothing but the placeholder
BAD_DATA=$(echo "$TRACKED" | grep -E '^data/' | grep -v '^data/\.gitkeep$')
[ -n "$BAD_DATA" ] && fail "tracked file(s) under data/ besides .gitkeep:\n$BAD_DATA" || ok "data/ contains only .gitkeep"

# 5. The personal profile seeding script, if it exists locally, must never be tracked
if echo "$TRACKED" | grep -q '^backend/app/seed_profile\.py$'; then
    fail "backend/app/seed_profile.py is tracked - this holds real personal profile data locally for some setups, it must stay git-ignored"
else
    ok "seed_profile.py not tracked"
fi

# 6. config/settings.json must never be tracked (settings.example.json is fine)
if echo "$TRACKED" | grep -q '^config/settings\.json$'; then
    fail "config/settings.json is tracked - only config/settings.example.json should be"
else
    ok "config/settings.json not tracked"
fi

# 7. Obvious secret-shaped strings in tracked text files
SECRET_HITS=$(echo "$TRACKED" | xargs -I{} sh -c 'test -f "{}" && file --mime "{}" | grep -q text && echo "{}"' 2>/dev/null \
  | xargs grep -lIE "sk-[a-zA-Z0-9]{20,}|AKIA[0-9A-Z]{16}|api[_-]?key[[:space:]]*[:=][[:space:]]*['\"][a-zA-Z0-9]{16,}|password[[:space:]]*[:=][[:space:]]*['\"][^'\"]{4,}|secret[[:space:]]*[:=][[:space:]]*['\"][a-zA-Z0-9]{8,}" 2>/dev/null)
[ -n "$SECRET_HITS" ] && fail "possible secret-shaped string(s) in:\n$SECRET_HITS" || ok "no obvious secret patterns found"

# 8. Known personal identifiers for this install (e.g. your email, phone).
# Read from a LOCAL, git-ignored file so the identifiers themselves are
# never committed by this script - that would defeat the point. One
# identifier per line. Create it locally with:
#   echo "you@example.com" >> .privacy-identifiers.local
#   echo "021 555 0100"    >> .privacy-identifiers.local
IDENTIFIERS_FILE=".privacy-identifiers.local"
if [ -f "$IDENTIFIERS_FILE" ]; then
    FOUND_ANY=0
    while IFS= read -r id; do
        [ -z "$id" ] && continue
        HIT=$(echo "$TRACKED" | xargs grep -lF "$id" 2>/dev/null)
        if [ -n "$HIT" ]; then
            fail "personal identifier found in:\n$HIT"
            FOUND_ANY=1
        fi
    done < "$IDENTIFIERS_FILE"
    [ "$FOUND_ANY" -eq 0 ] && ok "no known personal identifiers found in tracked files"
else
    echo "skip: no $IDENTIFIERS_FILE - add your email/phone there (one per line, git-ignored) for this check to run"
fi

echo
if [ "$FAIL" -eq 0 ]; then
    echo "Privacy check passed."
    exit 0
else
    echo "Privacy check FAILED. Do not push until the items above are resolved."
    exit 1
fi
