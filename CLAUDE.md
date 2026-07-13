# CLAUDE.md

## Development Standards

Before any development work in this repository, read `.standards/docs/standards/INDEX.md`
and the documents it lists. Treat them as binding:

- Specify before building: produce a `SPEC.md` per `.standards/docs/standards/spec_method.md`
  and pass the Spec Gate before writing code for any non-trivial change.
- Follow `.standards/docs/standards/code_conventions.md`, including its precedence order, which
  is authoritative for resolving any conflict between rules.
- Write tests before implementation (red-green-refactor), per the Testing section of `code_conventions.md`.
- Follow `.standards/docs/standards/ai_guidelines.md` for self-review and the Review Composition
  hierarchy (R1 internal, R2 cross-provider, R3 automated PR).
- Follow `.standards/docs/standards/github.md` for Conventional Commits, branch naming, and the
  PR, Issue, and README templates. No co-author or AI-attribution lines in commits.
- Record durable design decisions as ADRs under `docs/adr/`, promoted at the Spec Gate per
  `.standards/docs/standards/spec_method.md`; the README Engineering Decisions section indexes them.
- Token economy per `.standards/docs/standards/token_economy.md`: terse mode is allowed in
  conversation but never in `SPEC.md`, PR, Issue, or commit artifacts; it never overrides Safety
  or Correctness.
- All output in English.

## Project Adoption Notes

How the framework's generic rules instantiate in this repository:

- Branch naming: `type/NNN-short-description`, where `NNN` is the GitHub issue number
  (the project tracker). Example: `feat/130-persist-conversation-history`. This is the
  project form of the framework's `type/TASK-NNN-description`.
- Ephemeral `SPEC.md`: the spec lives at the repository root on the feature branch and
  is removed as the branch's final commit before merge. The PR's Spec Link points to the
  `SPEC.md` blob at a branch commit (or the content is pasted in the PR description).
- Review composition: the Codex R2 cross-provider pre-push gate
  (`.standards/docs/standards/codex_review.md`) is active here — the `codex` CLI is installed as the
  second-provider Reviewer and `core.hooksPath` is `.standards/.githooks`. Because the standards are a
  submodule, the framework hook's runner path (`scripts/codex-review.sh`) is supplied by a thin
  repo-root shim that forwards to `.standards/scripts/codex-review.sh`; without it the hook would
  silently no-op. R2 is advisory — record the Author and Reviewer models in every PR's Review Checklist,
  and note when R2 did not run (Codex absent, skipped, or bypassed). Local activation is
  `git config core.hooksPath .standards/.githooks` plus the shim; the framework's `setup.sh` is not
  yet submodule-aware (it points `core.hooksPath` at a non-existent root `.githooks`), so set the path
  manually until the upstream fix lands. R3 (automated PR review) is not configured.
- Domain docs: the project's ubiquitous language lives in `CONTEXT.md` at the repository root, and
  durable decisions live in `docs/adr/` (indexed by the README Engineering Decisions section). The
  framework's own process vocabulary — Developer, Author, Reviewer, SPEC, ADR, CRURA — is defined
  in `.standards/CONTEXT.md`.
