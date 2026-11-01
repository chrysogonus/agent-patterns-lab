#!/usr/bin/env bash
# Make a repository public and apply its GitHub security settings.
#
# Usage: scripts/go-public.sh OWNER/REPO
#   REQUIRED_CHECKS="check-a,check-b"  status checks the main ruleset requires (default: none)
#
# Safe to run again: every step checks the current state or uses an idempotent call.
# Needs gh (with `gh ruleset` and `--accept-visibility-change-consequences`), jq and git.
set -euo pipefail

if [[ $# -ne 1 || ! "$1" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]]; then
  echo "usage: $0 OWNER/REPO" >&2
  exit 2
fi
REPO="$1"
REQUIRED_CHECKS="${REQUIRED_CHECKS:-}"

step() { printf '\n==> %s\n' "$*"; }
info() { printf '    %s\n' "$*"; }

# Send a JSON body read from stdin; an empty path means the repository itself.
api_json() {
  local method="$1" path="$2"
  gh api --method "$method" -H "Accept: application/vnd.github+json" \
    "repos/$REPO${path:+/$path}" --input - >/dev/null
}

step "Preflight"
for tool in gh jq git; do
  command -v "$tool" >/dev/null || { echo "missing tool: $tool" >&2; exit 1; }
done
gh repo edit --help | grep -q -- '--accept-visibility-change-consequences' ||
  { echo "gh is too old: upgrade it (needs --accept-visibility-change-consequences)" >&2; exit 1; }
gh ruleset --help >/dev/null 2>&1 ||
  { echo "gh is too old: upgrade it (needs gh ruleset)" >&2; exit 1; }
perm="$(gh repo view "$REPO" --json viewerPermission --jq .viewerPermission)"
[[ "$perm" == "ADMIN" ]] || { echo "need ADMIN on $REPO, have $perm" >&2; exit 1; }
gh_version="$(gh --version)"
info "${gh_version%%$'\n'*}, admin on $REPO"

step "1. Visibility: public"
is_private="$(gh repo view "$REPO" --json isPrivate --jq .isPrivate)"
if [[ "$is_private" == "true" ]]; then
  gh repo edit "$REPO" --visibility public --accept-visibility-change-consequences
  info "now public"
else
  info "already public"
fi

step "2. Merge settings: squash only, delete branch on merge"
gh repo edit "$REPO" \
  --enable-squash-merge \
  --enable-merge-commit=false \
  --enable-rebase-merge=false \
  --delete-branch-on-merge
info "done"

step "2b. Wiki and projects: disable only if unused"
features="$(gh repo view "$REPO" --json hasWikiEnabled,hasProjectsEnabled)"
has_wiki="$(jq -r .hasWikiEnabled <<<"$features")"
has_projects="$(jq -r .hasProjectsEnabled <<<"$features")"
if [[ "$has_wiki" == "true" ]]; then
  if GIT_TERMINAL_PROMPT=0 git ls-remote "https://github.com/$REPO.wiki.git" >/dev/null 2>&1; then
    info "wiki has content: left enabled"
  else
    gh repo edit "$REPO" --enable-wiki=false
    info "wiki disabled (it had no pages)"
  fi
else
  info "wiki already disabled"
fi
if [[ "$has_projects" == "true" ]]; then
  owner="${REPO%%/*}" name="${REPO##*/}"
  # shellcheck disable=SC2016  # $o and $n are GraphQL variables, not shell ones
  query='query($o:String!,$n:String!){repository(owner:$o,name:$n){projectsV2(first:1){totalCount}}}'
  if count="$(gh api graphql -f query="$query" -f o="$owner" -f n="$name" \
      --jq .data.repository.projectsV2.totalCount 2>/dev/null)"; then
    if [[ "$count" == "0" ]]; then
      gh repo edit "$REPO" --enable-projects=false
      info "projects disabled (none linked)"
    else
      info "$count project(s) linked: left enabled"
    fi
  else
    info "cannot list projects (token needs read:project): left enabled"
  fi
else
  info "projects already disabled"
fi

step "3. Secret scanning and push protection"
# advanced_security is deliberately absent: sending it for a public repo returns 422.
api_json PATCH "" <<'JSON'
{"security_and_analysis": {
  "secret_scanning": {"status": "enabled"},
  "secret_scanning_push_protection": {"status": "enabled"}}}
JSON
info "enabled"

step "4. Dependabot alerts and fixes, private vulnerability reporting, immutable releases"
for feature in vulnerability-alerts automated-security-fixes \
    private-vulnerability-reporting immutable-releases; do
  gh api --method PUT "repos/$REPO/$feature" >/dev/null
  info "$feature: enabled"
done

step "5. Code scanning default setup"
api_json PATCH code-scanning/default-setup <<'JSON'
{"state": "configured"}
JSON
info "configured (the first analysis runs in the background)"

step "6. Actions: read-only GITHUB_TOKEN, approval for fork PRs"
api_json PUT actions/permissions/workflow <<'JSON'
{"default_workflow_permissions": "read", "can_approve_pull_request_reviews": false}
JSON
info "default token read-only; Actions may not approve PRs"
if out="$(gh api --method PUT "repos/$REPO/actions/permissions/fork-pr-contributor-approval" \
    -f approval_policy=all_external_contributors 2>&1)"; then
  info "fork PRs from all external contributors need approval"
elif grep -q 'HTTP 404' <<<"$out"; then
  info "endpoint not available: set it in Settings > Actions > General >"
  info "'Approval for running fork pull request workflows from contributors'"
else
  echo "$out" >&2
  exit 1
fi

step "7. Rulesets"
existing="$(gh api "repos/$REPO/rulesets" --jq '.[].name')"

if grep -qxF main <<<"$existing"; then
  info "main: exists, skipped"
else
  checks="$(jq -cn --arg c "$REQUIRED_CHECKS" \
    '$c | split(",") | map(gsub("^\\s+|\\s+$"; "")) | map(select(length > 0)) | map({context: .})')"
  jq -n --argjson checks "$checks" '{
    name: "main",
    target: "branch",
    enforcement: "active",
    conditions: {ref_name: {include: ["~DEFAULT_BRANCH"], exclude: []}},
    rules: ([
      {type: "deletion"},
      {type: "non_fast_forward"},
      {type: "pull_request", parameters: {
        required_approving_review_count: 0,
        dismiss_stale_reviews_on_push: false,
        require_code_owner_review: false,
        require_last_push_approval: false,
        required_review_thread_resolution: false}}
    ] + (if ($checks | length) > 0 then [{type: "required_status_checks", parameters: {
        strict_required_status_checks_policy: false,
        required_status_checks: $checks}}] else [] end))
  }' | api_json POST rulesets
  info "main: created (required checks: ${REQUIRED_CHECKS:-none})"
fi

if grep -qxF release-tags <<<"$existing"; then
  info "release-tags: exists, skipped"
else
  api_json POST rulesets <<'JSON'
{"name": "release-tags", "target": "tag", "enforcement": "active",
 "conditions": {"ref_name": {"include": ["refs/tags/v*"], "exclude": []}},
 "rules": [{"type": "deletion"}, {"type": "non_fast_forward"}]}
JSON
  info "release-tags: created"
fi

step "8. Verify"
info "security_and_analysis:"
gh api "repos/$REPO" --jq .security_and_analysis
info "rulesets:"
gh ruleset list --repo "$REPO"
info "workflow permissions:"
gh api "repos/$REPO/actions/permissions/workflow"

printf '\nDone: %s\n' "$REPO"
