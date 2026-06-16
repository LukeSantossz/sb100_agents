# bcrypt + JWT authentication gate

`/chat` needs stateless, revocable authentication that fits a stateless API. We hash passwords
with bcrypt and gate `/chat` with a signed JWT, validating the token signature and confirming the
User still exists on every request.

## Status

Accepted.

## Considered Options

- **bcrypt + JWT (chosen)**: stateless and timing-safe; revoked instantly when a User is deleted,
  because each request re-checks existence.
- **Session cookies**. Rejected — server-side session state that does not fit a stateless API.
- **Static API keys**. Rejected — no per-User identity and awkward rotation and revocation.

## Consequences

- One database lookup per request buys instant revocation.
- Breaking change: Users created before the gate (SHA-256 hashes) must re-register.
- Login and registration carry per-IP rate limits to blunt brute-force attempts.
