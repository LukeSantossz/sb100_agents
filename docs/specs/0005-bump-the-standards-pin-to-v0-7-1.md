# SPEC: fix(standards): bump the pin to v0.7.1 so the generated instructions resolve

## Problem

`CLAUDE.md` sends every session to `docs/agents/issue-tracker.md`,
`docs/agents/triage-labels.md` and `docs/agents/domain.md`. None of those paths
exists here: this repository vendors the corpus, so those documents are inside
`.standards/docs/agents/`, and `mf agents sync` rewrote only the
`docs/standards/` prefix.

Nothing reported it. `mf check agents` compares the generated file against the
source it was generated from, which matched, so the gate passed over a file
whose three skill references resolve to nothing.

## Scope

- Includes: the `.standards` pin at `v0.7.1`; `.framework.lock`; `CLAUDE.md`
  regenerated with the references rewritten.
- Does NOT include: adopting `paths.agents_overlay`, which `v0.7.0` added and
  this repository has no project-specific instructions to put in yet; any
  change to the standards themselves, which the submodule supplies; the CI
  changes on this branch, which are specified separately.

## Acceptance Criteria

- `every_agent_document_the_generated_file_names_exists_in_the_checkout`
- `mf check agents` passes.

## Reproducibility

```sh
git submodule status .standards                        # v0.7.1
grep -o 'docs/agents/[a-z-]*\.md' CLAUDE.md | sort -u  # each one under .standards/
mf check agents
```

Versions: `mf` v0.7.1.

## Risks and Assumptions

- Assumption: nothing else in this repository depended on the unrewritten paths.
  They resolved to nothing, so nothing could have.
