<!-- Title: Conventional Commits format, e.g. `feat(auth): implement password recovery` -->

## 1. Context

- **Motivation:** <!-- reason for the change -->
- **Task Link:** <!-- issue URL -->
- **Spec Link:** <!-- link to the SPEC.md blob at a branch commit, or "trivial change — no spec" -->

## 2. What Was Done

<!-- technical changes in summary form -->

## 3. How to Test

1. Check out the branch.
2. Install dependencies (`uv sync`).
3. Run the project.
4. Verify the build runs without errors.

## 4. Evidence

<!-- screenshots or videos if the change is visual; omit if backend or configuration only -->

## 5. Self-Review Checklist

- [ ] Self-review done in the Files Changed tab.
- [ ] Spec approved at the Gate before implementation, and the change matches its Scope (per `spec_method.md`).
- [ ] Each Acceptance Criterion has a passing test; tests were written before their implementation.
- [ ] Commented-out code and unnecessary debug statements removed.
- [ ] Code follows the project style guide.
- [ ] New dependencies work without breaking the build.
- [ ] Review layers recorded:
  - R1 (internal review): <!-- ran / did not run; Author model -->
  - R2 (cross-provider review): not available in this project — human CRURA review stands in.
  - R3 (automated PR review): not configured.
