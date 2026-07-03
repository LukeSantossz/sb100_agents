# Untrusted external input in agentic CI

The agentic CI workflows run `claude-code-action` with `contents`/`pull-requests`/`issues: write`
and `ANTHROPIC_API_KEY` in scope. Any externally controlled text — a GitHub issue title/body, a
comment — must enter such a job only as **isolated data under least privilege**, never interpolated
into the GitHub Actions expression context or spliced into the agent's instruction layer. Concretely
for `claude-auto.yml`: capture the issue title/body at trigger time into an isolated file via a
`run:` step reading step `env:` (not `${{ }}` in a code/prompt context), pass only the safe integer
`github.event.issue.number` into the agent `prompt:`, frame the file as untrusted data the agent must
never treat as instructions, and drop the unused `id-token: write`. The barrier is defense in depth:
no untrusted expansion at the workflow layer, least privilege, and the existing human merge review.

## Status

Accepted. Applied to `claude-auto.yml` (SPEC `docs/specs/0001-isolate-issue-body-from-agent-prompt.md`).
`claude-respond.yml` and any future agentic workflow must follow the same rule; their alignment is a
tracked follow-up, not covered here.

## Considered Options

- **Isolated-file capture + issue-number-only prompt + least privilege (chosen)**: eliminates GitHub
  Actions template injection deterministically (the untrusted string is never `${{ }}`-expanded into a
  code or prompt context), captures the content at trigger time, and keeps the agent's instruction
  layer authored by us. Least privilege (dropping `id-token: write`) shrinks the blast radius.
- **Fetch-by-number at runtime** (the prompt carries only `#number`; the agent runs `gh issue view`):
  also safe against template injection, but depends on `gh`/network inside the action and re-reads
  mutable content between labeling and fetch. Kept as a viable fallback.
- **Inline delimit/escape** the body inside the prompt string: rejected — `${{ github.event.issue.body }}`
  is still expanded into the expression/prompt context, so fence/expression syntax in the body can
  still break out; in-band escaping is fragile.
- **Remove the auto-implement workflow**: rejected — discards a wanted capability the isolation pattern
  makes safe enough to keep behind human merge review.

## Consequences

- Template injection at the GitHub Actions layer is closed for `claude-auto.yml`.
- Residual agent-layer prompt injection is **mitigated, not eliminated**: the untrusted body still
  enters the agent's context when it reads the isolated file. The hard barriers remain least privilege
  plus human merge review; the framing (treat as untrusted data, do not exfiltrate) lowers, not
  removes, the risk. Declared, not silently accepted.
- A repo-wide rule now governs untrusted input in agentic CI; `claude-respond.yml` is not yet aligned,
  so the guarantee is per-workflow until the follow-up lands.
- `id-token: write` is removed from `claude-auto`; re-add it narrowly only if a future step needs OIDC.
- A deterministic YAML-assertion test enforces the pattern for `claude-auto.yml`, so a regression that
  reintroduces the untrusted interpolation or the extra privilege fails CI.
