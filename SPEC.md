# SPEC: docs: translate SETUP.md to English and remove stale newcomer guide

## Problem

The framework requires all documentation in English, but `SETUP.md` (the deployment guide the English README depends on) is fully in Portuguese, `GUIA-NOVOS-CONTRIBUIDORES.md` is a stale Portuguese doc contradicting CONTRIBUTING/README, and `.dockerignore`/`.env.example`/`Dockerfile.api` carry Portuguese comments.

## Design Decision

Translate `SETUP.md` in place preserving its structure and section numbering, updating the §9.1 heading anchor and the README link to it in the same commit; remove the newcomer guide entirely (its accurate content already lives in README/CONTRIBUTING); translate the comment lines of the three config files without touching any directive or value.

## Alternatives Considered

- Rewrite the newcomer guide in English instead of removing it: rejected — it duplicates README/CONTRIBUTING, references the removed `.claude` framework, and carries stale numbers (~24% coverage); the author chose removal at the adoption review.
- Keep `SETUP.md` in Portuguese as a product-locale exception: rejected — it is contributor documentation, not user-facing product copy, and the English README delegates required Linux-deploy steps to it.

## Scope

- Includes: `SETUP.md` full translation, `README.md` §9.1 anchor update, `git rm GUIA-NOVOS-CONTRIBUIDORES.md`, comment-line translation in `.dockerignore`, `.env.example`, `Dockerfile.api`.
- Does NOT include: code or test changes (#138, #139); governance docs (#136); any change to directives, env values, Docker instructions, or compose behavior; the `.standards/` submodule.

## Acceptance Criteria

- setup_md_contains_no_portuguese_text
- readme_linux_deploy_link_resolves_to_new_english_anchor
- newcomer_guide_no_longer_tracked
- config_files_comments_are_english_with_values_unchanged

## Reproducibility

Doc-only change. Verification: `git grep -nP "[\x{00C0}-\x{00FF}]" -- SETUP.md .dockerignore .env.example Dockerfile.api README.md` returns nothing; `test -f GUIA-NOVOS-CONTRIBUIDORES.md` fails; `docker compose config` still parses (no directive touched).

## Risks and Assumptions

- Risk: anchor drift — GitHub derives anchors from headings, so the README link is updated in the same commit as the §9.1 retitle.
- Assumption: no external site links to the old Portuguese anchors.
- Assumption: `.env.example` values (including the ZeroTier placeholders) stay byte-identical; only comments change.
