# SPEC: docs: adopt development-standards governance and GitHub templates

## Problem

The repository's governance documents contradict the adopted standards framework (wrong `token_economy.md` path in `CLAUDE.md`, divergent branch convention in `CONTRIBUTING.md`/`README.md`) and the PR/Issue templates required by `.standards/docs/standards/github.md` do not exist.

## Design Decision

Fix the governance docs in place and add the two GitHub templates, instantiating the framework's generic rules to this project: branch format `type/NNN-short-description` with NNN = GitHub issue number, ephemeral `SPEC.md` (repo root on the feature branch, removed before merge), and the R2 fallback (no second-provider reviewer available — R1 internal review plus human CRURA review stand in, recorded per PR).

## Alternatives Considered

- Inline the token-economy rule into `CLAUDE.md` instead of referencing the file: rejected — the file exists at `.standards/token_economy.md`; only the path is wrong, and duplicating its content would drift.
- Keep `type/short-description` (current CONTRIBUTING) and note it as a framework deviation: rejected — the framework's `TASK-NNN` maps naturally to the GitHub issue number now that issues are the project tracker, and traceability from branch to issue is worth the small friction.
- Store `SPEC.md` files permanently under `docs/specs/`: rejected by the author at the adoption review — ephemeral SPEC keeps the repo lean; the PR links the SPEC blob at a branch commit for audit.

## Scope

- Includes: `CLAUDE.md` (path fix + Project Adoption Notes), `CONTRIBUTING.md` (branch convention, Spec Gate, test-first, review composition), `README.md` Contributing line, `.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/task.md`, `.github/ISSUE_TEMPLATE/config.yml`.
- Does NOT include: any code or test changes; SETUP.md translation or newcomer-guide removal (#137); code text translation (#138); prompt/user-string translation (#139); changes inside the `.standards/` submodule.

## Acceptance Criteria

- claude_md_references_existing_token_economy_path
- claude_md_contains_project_adoption_notes_with_branch_spec_and_r2_rules
- contributing_branch_pattern_includes_issue_number
- contributing_documents_spec_gate_and_test_first_policy
- readme_contributing_summary_matches_new_branch_pattern
- pr_template_contains_review_layers_record
- issue_template_contains_five_issue_model_sections

## Reproducibility

Doc-only change. Verification: `git grep -n "type/short-description"` returns nothing; `git grep -n "docs/standards/token_economy"` returns nothing in tracked repo files (submodule excluded); `git submodule status` shows `.standards` unchanged.

## Risks and Assumptions

- Assumption: the `.standards` submodule keeps `token_economy.md` at its root; if upstream moves it under `docs/standards/`, the `CLAUDE.md` path must follow.
- Assumption: GitHub renders `.github/ISSUE_TEMPLATE/task.md` only for new issues; the 44 open issues are unaffected.
- Risk: PRs #137-#139 are opened before this template merges, so their bodies replicate the template manually.
