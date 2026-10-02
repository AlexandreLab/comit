#!/bin/bash
# Refuse a commit on a feature branch in the main checkout.
#
# Several agent sessions share the main checkout. If one switches it to its branch, another
# session's next commit lands there (2026-10-02: a site-services commit landed on
# docs/process-version-vs-cohort). Feature work belongs in its own worktree under
# .worktrees/<branch>, where no other session can move the branch under it.
#
# Linked worktrees are not checked. The main checkout may commit only on main, which a
# fast-forward or a merge from the fork can need.
set -euo pipefail

if [[ "${ALLOW_MAIN_CHECKOUT_COMMIT:-}" == "1" ]]; then
  exit 0
fi

git_dir="$(cd "$(git rev-parse --git-dir)" && pwd -P)"
common_dir="$(cd "$(git rev-parse --git-common-dir)" && pwd -P)"
if [[ "$git_dir" != "$common_dir" ]]; then
  exit 0  # a linked worktree
fi

branch="$(git branch --show-current)"
if [[ -z "$branch" || "$branch" == "main" ]]; then
  exit 0
fi

top="$(git rev-parse --show-toplevel)"
dir="${branch//\//-}"
cat >&2 <<EOF
❌ Commit refused: branch '$branch' is checked out in the main checkout ($top).

Other sessions share this checkout and can switch its branch under you. Commit from the
branch's own worktree instead:

   git switch main
   git worktree add .worktrees/$dir $branch
   cd .worktrees/$dir

If you are sure no other session uses this checkout:

   ALLOW_MAIN_CHECKOUT_COMMIT=1 git commit ...
EOF
exit 1
