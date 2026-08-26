# SPEC: chore: adopt the v0.6.2 standards harness

## Problem

`CLAUDE.md` states that the Codex R2 pre-push gate is active here and that
`core.hooksPath` is `.standards/.githooks`; the setting is unset, the shim it
describes forwards to a runner the upstream framework deleted, and the guard
written to catch exactly this — `tests/test_r2_gate_wiring.py` — skips itself
when `.standards` is absent, which it was, so the suite reported green over a
gate that had never once fired.

## Design Decision

Move the pin to `v0.6.2` and adopt the harness that tag ships, rather than
restoring the shim. The framework replaced its shell runner with the `mf` binary
and now ships its hooks into the adopting repository, so the indirection this
repository built — a repo-root shim forwarding into the submodule — has nothing
left to forward to and no reason to exist.

The wiring guard is rewritten rather than deleted. It was right to exist and
wrong in what it watched: it asserted which file the hook execs and never
whether git would reach the hook. It now executes both hooks against an unusable
runner and asserts they refuse, checks `core.hooksPath` directly, and asserts no
second corpus exists — all without a skip, because a guard that can skip itself
into silence is the failure it was written for.

## Alternatives Considered

- **Restore the shim and keep the pin.** Rejected: `.standards/scripts/codex-review.sh`
  no longer exists at any tag this repository can move to, so the shim would
  forward into nothing on the next submodule update.
- **Delete the wiring guard along with the wiring it tested.** Rejected: the
  guard's subject — "does the gate actually fire" — is still the right question,
  and this repository is the reason anyone knows it needed asking.
- **Keep the ephemeral root `SPEC.md` convention.** Rejected: the standards this
  repository binds itself to replaced it with a durable archive, `mf check
  records` enforces that archive, and `docs/specs/` here already holds two
  entries — so the documented convention and the practised one had already
  parted company.

## Scope

- Includes: the `.standards` pin at `v0.6.2`; `.framework.toml` and
  `.framework.lock`; `core.hooksPath` pointing at the versioned hooks the tag
  ships; deletion of `scripts/codex-review.sh`; `CLAUDE.md` regenerated and
  `AGENTS.md` generated from the submodule's instruction source;
  `tests/test_r2_gate_wiring.py` rewritten against the new wiring; the R1, R2
  and explain chains and the backends they name; `CONTRIBUTING.md`'s spec
  section and conventions table describing the durable archive and the review
  layers that now run.
- Does NOT include: `CONTEXT.md`, which already holds this project's domain
  language and is not what changed; an R3 chain, because no automated
  pull-request reviewer is wired here and naming one that does not run would
  read as a review that happened; any change to `agent/`, `api/`, `core/`,
  `retrieval/`, `generation/`, `memory/`, `verification/` or the CI workflow.

## Acceptance Criteria

- `mf_check_passes_every_gate_in_this_repository`
- `core_hooks_path_points_at_the_versioned_hooks`
- `both_hooks_refuse_when_the_runner_is_unusable`
- `the_wiring_guard_has_no_skip_that_can_silence_it`
- `no_second_standards_corpus_exists_beside_the_submodule`
- `no_file_outside_the_submodule_references_codex_review`
- `mf_doctor_resolves_both_r2_backends_on_a_machine_that_has_them`

## Reproducibility

```sh
git submodule update --init
mf check
mf doctor
pytest tests/test_r2_gate_wiring.py
grep -rn "codex-review" . --exclude-dir=.standards --exclude-dir=.git
```

Versions: `mf` v0.6.2; `.standards` at tag `v0.6.2`.

## Risks and Assumptions

- Assumption: nothing outside this repository invokes `scripts/codex-review.sh`.
  It was called by the framework's old hook and by the guard, both replaced here.
- Risk: the backend definitions are copied from the framework's own
  `.framework.toml` rather than referenced, because a backend is declared per
  repository and there is no mechanism for referencing one from elsewhere. They
  can drift from upstream, and keeping them in step is a manual step recorded
  here rather than hidden.
- Risk: the pre-push gate now fails closed, so a push stops when `mf` is not on
  `PATH`. That is the intended behaviour and the reason the old hook's silence
  was a defect; `git push --no-verify` remains git's own bypass.
- Risk: R2 now runs on every push, which costs a model call and time a push did
  not cost before. It is advisory — `roles.r2.blocking` is left undeclared — and
  an unavailable backend is reported rather than treated as a review.
