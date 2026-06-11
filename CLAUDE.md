# CLAUDE.md

## Development Standards

Before any development work in this repository, read `.standards/docs/standards/INDEX.md`
and the documents it lists. Treat them as binding:

- Specify before building: produce a `SPEC.md` per `.standards/docs/standards/spec_method.md`
  and pass the Spec Gate before writing code for any non-trivial change.
- Follow `.standards/docs/standards/code_conventions.md`, including its precedence order.
- Write tests before implementation (red-green-refactor), per the Testing section of `code_conventions.md`.
- Follow `.standards/docs/standards/ai_guidelines.md` for self-review and the Review Composition
  hierarchy (R1 internal, R2 cross-provider, R3 automated PR).
- Follow `.standards/docs/standards/github.md` for Conventional Commits, branch naming, and templates.
  No co-author or AI-attribution lines in commits.
- Token economy per `.standards/token_economy.md`.
- All output in English.

## Project Adoption Notes

How the framework's generic rules instantiate in this repository:

- Branch naming: `type/NNN-short-description`, where `NNN` is the GitHub issue number
  (the project tracker). Example: `feat/130-persist-conversation-history`. This is the
  project form of the framework's `type/TASK-NNN-description`.
- Ephemeral `SPEC.md`: the spec lives at the repository root on the feature branch and
  is removed as the branch's final commit before merge. The PR's Spec Link points to the
  `SPEC.md` blob at a branch commit (or the content is pasted in the PR description).
- Review composition: no second-provider Reviewer (R2) is available in this project.
  R1 internal review plus the human CRURA review stand in for R2; record this in every
  PR's Self-Review Checklist. R3 (automated PR review) is not configured.
