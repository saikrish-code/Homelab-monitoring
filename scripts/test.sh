#!/usr/bin/env bash
# CI-friendly test runner: lint, syntax, generated-project sanity, plugin + mock-bridge tests.
# Generates a throwaway project in a temp dir, so it never touches ./homelab-monitoring or its .env.
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-python3}"
command -v "$PY" >/dev/null 2>&1 || PY=python

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
PROJECT="$TMP/proj"

echo "==> bash syntax: setup.sh"
bash -n setup.sh

echo "==> generate project"
bash setup.sh "$PROJECT" >/dev/null

echo "==> bash syntax: generated scripts"
for f in "$PROJECT"/scenarios/*.sh "$PROJECT"/nagios/entrypoint.sh "$PROJECT"/db01/init/*.sh; do
  bash -n "$f" && echo "  ok $f"
done

if command -v shellcheck >/dev/null 2>&1; then
  echo "==> shellcheck"
  shellcheck -S warning setup.sh scripts/test.sh "$PROJECT"/scenarios/*.sh "$PROJECT"/nagios/entrypoint.sh
else
  echo "==> shellcheck not installed, skipping"
fi

echo "==> python compile"
for f in "$PROJECT"/integration/*.py "$PROJECT"/nagios/plugins/*.py tests/*.py; do
  "$PY" -I -c "import sys; compile(open(sys.argv[1], encoding='utf-8').read(), sys.argv[1], 'exec')" "$f"
  echo "  ok $f"
done

echo "==> docs present"
for f in web-down nginx-down bad-config db-crash disk-fill cpu-load net-cut; do
  [ -s "$PROJECT/docs/runbooks/$f.md" ] || { echo "FAIL: missing runbook $f"; exit 1; }
done
[ -s "$PROJECT/docs/diagrams/architecture.md" ] || { echo "FAIL: missing architecture diagram"; exit 1; }
ls "$PROJECT"/docs/rca/*drill*.md >/dev/null

echo "==> .env hygiene"
grep -qx '.env' "$PROJECT/.gitignore" || { echo "FAIL: .env not in generated .gitignore"; exit 1; }

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  echo "==> docker compose config"
  (cd "$PROJECT" && docker compose config -q)
else
  echo "==> docker not available, skipping compose config"
fi

echo "==> unit tests (plugin + mock ServiceNow bridge)"
PROJECT_DIR="$PROJECT" "$PY" -W ignore -m unittest discover -s tests -v

echo "ALL TESTS PASSED"
