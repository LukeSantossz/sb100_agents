# SPEC: fix(ci): isolate untrusted issue content from the claude-auto agent prompt

## Problem
`.github/workflows/claude-auto.yml` interpolates attacker-controllable `github.event.issue.title`/`body` directly into a write-privileged agent `prompt:` (and into the GitHub Actions expression context), so a single labeled issue can drive an agent holding `contents`/`pull-requests`/`issues`/`id-token: write` and `ANTHROPIC_API_KEY` via template and prompt injection.

## Design Decision
Capture the issue title and body at trigger time into an isolated file through a `run:` step that reads them from step `env:` (never `${{ }}`-expanded into a code or prompt context), pass only the safe integer `github.event.issue.number` into the agent `prompt:`, and instruct the agent — in a static instruction block the issue content cannot override — to read that file as UNTRUSTED DATA describing the request, never as instructions. Additionally reduce the job to least privilege by removing the unused `id-token: write`, and add an explicit "do not exfiltrate secrets; a human reviews before merge" directive. This eliminates GitHub Actions template injection at the workflow layer and shrinks the blast radius; residual agent-layer prompt injection is mitigated — not eliminated — by the untrusted-data framing, least privilege, and the existing human merge barrier.

## Alternatives Considered
1. **Inline delimit/escape** the body inside the prompt string (wrap it in a fenced block). Rejected: `${{ github.event.issue.body }}` is still expanded into the Actions expression/prompt context, so a body carrying fence or expression syntax can still break out; in-band escaping of untrusted content is fragile and not robust to future template edits.
2. **Fetch-by-number at runtime** — the prompt passes only `#number` and the agent runs `gh issue view` itself. Rejected as primary (kept as a viable fallback): it is also safe against template injection, but it depends on `gh`/network availability inside the action and re-reads mutable content (the body can change between labeling and fetch); the isolated-file capture is deterministic and is the approach the issue's recommended fix names.
3. **Remove the auto-implement workflow entirely.** Rejected: discards a wanted capability; the risk is addressable with isolation plus least privilege rather than removal.

## Scope
- Includes:
  - `.github/workflows/claude-auto.yml`: capture `issue.title`/`issue.body` via the existing `env:`-based `run:` step into an isolated file (e.g. `${RUNNER_TEMP}/issue-context.md` or a checked-out working path the agent can read); remove both from the `prompt:` `${{ }}` interpolation; reference only `github.event.issue.number` in the prompt; add a static untrusted-data / anti-exfiltration / human-review instruction block; remove `id-token: write` from the job `permissions`.
  - A deterministic YAML-assertion test under `tests/` that fails on the current file and passes on the fixed one.
- Does NOT include:
  - `.github/workflows/claude-respond.yml` (its identical `id-token: write` and trigger model — a follow-up / Stage 0 item 3).
  - Pinning actions by commit SHA and adding `persist-credentials: false` (Stage 0 item 3 / #118 / U6).
  - Any change to `claude-code-action` version, model, `--max-turns`, or the label-trigger gate.
  - Broader agentic-CI redesign (dedicated GitHub App, fork-safe PR creation, runner egress controls).

## Acceptance Criteria
- `prompt_contains_no_untrusted_issue_expression`: the `Run Claude Code` step's `prompt` contains neither `github.event.issue.body` nor `github.event.issue.title`.
- `prompt_references_issue_by_number_only`: the prompt references `github.event.issue.number` and directs the agent to the isolated file.
- `issue_title_and_body_appear_only_under_step_env`: `github.event.issue.title`/`body` appear only inside a step `env:` mapping, never inline in a `run:` or `with:` `${{ }}` expression (guards template injection).
- `claude_auto_job_omits_id_token_write`: the job `permissions:` block does not grant `id-token: write`.
- `existing_suite_still_green`: `pytest tests/ -m "not requires_infra"` passes (no regression).

## Reproducibility
- Red→green: `pytest tests/test_claude_auto_prompt_isolation.py -v` (new test) fails on HEAD `fix/111` before the workflow edit and passes after it.
- Regression guard: `pytest tests/ -m "not requires_infra"`.
- Versions: as pinned in `uv.lock` (pytest >= 7; Python 3.12). No randomness; no seed required.

## Risks and Assumptions
- Assumption: `id-token: write` is unused — no OIDC consumer (`aws-actions/*`, cloud login) exists in the workflow; removal is safe. Re-add narrowly if a future step needs OIDC.
- Assumption: `claude-code-action@v1` runs the supplied `prompt` as the agent's instructions and the agent can read a file on the runner — consistent with current usage; no new action input is invented.
- Assumption: `github.event.issue.number` is a GitHub-controlled integer, not attacker-controllable — true.
- Residual risk: agent-layer prompt injection is mitigated, not eliminated — the untrusted body still enters the agent's context when it reads the file; the hard barriers remain least privilege plus human merge review. Declared, not silently accepted.
- Invalidated if: the action changes how `prompt`/inputs are evaluated, or a future requirement needs the body inline in the prompt.

## Design Decision -> ADR (proposed at the Spec Gate)
Promote the reusable rule — "untrusted external input enters agentic CI only as isolated data under least privilege, never as interpolated instructions" — to `docs/adr/0011-*` at the gate, since `claude-respond.yml` and future agentic workflows must follow it. The Developer decides promotion at the gate.
