# SQLite for persistence

At current single-node scale, persistence should be zero-ops. We use SQLite for authentication and
conversation records, with PostgreSQL named as the migration path once writes contend.

## Status

Accepted.

## Considered Options

- **SQLite (chosen)**: single file, zero-ops, fits one API process.
- **PostgreSQL**. Rejected for now — operational overhead unjustified at current scale; kept as
  the documented migration path once write contention appears.

## Consequences

- Single-writer storage: it fits one process and does not support horizontal scaling.
- A documented Windows + Docker bind-mount pitfall (the DB path created as a directory) is guarded
  with an explicit `RuntimeError` at startup rather than failing silently.
- Migrating to PostgreSQL is the path once write contention appears.
