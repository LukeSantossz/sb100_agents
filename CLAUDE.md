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
- Token economy per `.standards/docs/standards/token_economy.md`.
- All output in English.
