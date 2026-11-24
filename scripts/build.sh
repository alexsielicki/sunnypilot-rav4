#!/usr/bin/env bash
# Build the rav4-prebuilt branch: sunnypilot's tn-prebuilt snapshot + every patch in patches/ (applied in name order).
#
# Env:
#   GH_TOKEN   token allowed to push to this repo (in Actions: github.token)
#   REPO       owner/name of this repo (in Actions: github.repository)
#   FORCE      "true" to rebuild even if nothing changed
#   DRY_RUN    "true" to build and check, but not push
set -euo pipefail

UP_REPO=https://github.com/sunnypilot/openpilot.git
UP_BRANCH=tn-prebuilt
OUT_BRANCH=rav4-prebuilt
TOOLS="$(cd "$(dirname "$0")/.." && pwd)"
FORCE="${FORCE:-false}"
DRY_RUN="${DRY_RUN:-false}"

shopt -s nullglob
patches=("$TOOLS"/patches/*.patch)
sha() { if command -v sha256sum >/dev/null; then sha256sum; else shasum -a 256; fi; }
patch_hash=$( (for p in ${patches[@]+"${patches[@]}"}; do basename "$p"; cat "$p"; done) | sha | cut -c1-12)

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cd "$work"
git init -q
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git remote add up "$UP_REPO"
git remote add origin "https://x-access-token:${GH_TOKEN}@github.com/${REPO}.git"

git fetch -q --depth 1 up "$UP_BRANCH"
up_sha=$(git rev-parse FETCH_HEAD)
up_subject=$(git log -1 --format=%s FETCH_HEAD)
stamp="upstream: $UP_BRANCH $up_sha | patches: $patch_hash"
echo "upstream $UP_BRANCH: $up_sha ($up_subject)"
echo "patches (${#patches[@]}): $patch_hash"

prev=""
if git fetch -q --depth 1 origin "$OUT_BRANCH" 2>/dev/null; then
  prev=$(git rev-parse FETCH_HEAD)
  if git log -1 --format=%B "$prev" | grep -qF "$stamp" && [ "$FORCE" != "true" ]; then
    echo "$OUT_BRANCH is up to date ($prev); nothing to do"
    exit 0
  fi
fi

git checkout -q --detach "$up_sha"
for p in ${patches[@]+"${patches[@]}"}; do
  echo "applying $(basename "$p")"
  if ! git apply --index --whitespace=nowarn "$p"; then
    echo "::error::$(basename "$p") no longer applies to $UP_BRANCH $up_sha. $OUT_BRANCH was left unchanged; update the patch."
    exit 1
  fi
done
# Upstream workflow files never belong on the car branch (and GITHUB_TOKEN can't push them).
git rm -r -q --cached --ignore-unmatch .github/workflows

tree=$(git write-tree)
up_tree=$(git rev-parse "$up_sha^{tree}")
if [ ${#patches[@]} -eq 0 ] && [ "$tree" != "$up_tree" ]; then
  echo "::error::with no patches the tree should equal upstream's, but it doesn't"; exit 1
fi
names=$(for p in ${patches[@]+"${patches[@]}"}; do echo "  - $(basename "$p")"; done)
msg=$(printf '%s + %d patch(es)\n\n%s\n%s\n' "$up_subject" "${#patches[@]}" "$stamp" "$names")
commit=$(git commit-tree "$tree" ${prev:+-p "$prev"} -m "$msg")
echo "built $commit (tree $tree; upstream tree $up_tree)"

if [ "$DRY_RUN" = "true" ]; then echo "dry run: not pushing"; exit 0; fi
git push -q origin "$commit:refs/heads/$OUT_BRANCH"
echo "pushed $OUT_BRANCH -> $commit"
