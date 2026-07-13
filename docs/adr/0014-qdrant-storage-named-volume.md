# Qdrant storage on a named Docker volume, not a host bind mount

On the Windows/Docker Desktop development machine the Qdrant container repeatedly wedged:
metadata operations (`count`, collection info) stayed instant, but every vector search hung and
the server returned `500 "Operation retrieve timed out after 60s"`, after which the container
became un-killable (`docker restart`/`kill` → "tried to kill container, but did not receive an
exit event"), recoverable only by restarting the Docker/WSL2 engine.

Root cause (from `docker logs` + `docker inspect`): the storage was a **host bind mount to a
Windows path inside OneDrive** (`.../OneDrive/Desktop/sb100_agents/qdrant_storage`). Docker Desktop
exposes Windows paths into the WSL2 VM as a **FUSE/virtiofs** filesystem — Qdrant logs
`Filesystem check failed for storage path ./storage. Details: FUSE filesystems may cause data
corruption due to caching issues` and `Not using multi-mmap due to limited support` — and OneDrive
syncs the live database files underneath. A datastore doing constant `mmap`/`fsync` over
FUSE+OneDrive stalls, hanging both queries and graceful shutdown (`SIGTERM` → workers never exit →
zombie). `OOMKilled=false`, so it was not memory pressure.

We move Qdrant storage to a **named Docker volume** (`qdrant_storage:/qdrant/storage`), which lives
on the native ext4 filesystem inside the WSL2 VM — no FUSE, no OneDrive. After the change the
FUSE filesystem-check error is gone from startup and vector search is stable.

## Status

Accepted.

## Considered Options

- **Named Docker volume (chosen)**: the standard way to persist a database under Docker Desktop on
  Windows. Native ext4 in the VM removes both the FUSE/virtiofs layer and OneDrive sync from the
  datastore's I/O path. Data survives container recreation.
- **Keep the bind mount, move the repo out of OneDrive**: removes OneDrive but not the
  FUSE/virtiofs layer — any Windows-path bind mount is still FUSE inside WSL2, so the mmap stalls
  can persist. Rejected as insufficient. (Moving the repo off OneDrive is still good hygiene for
  the git working tree and `.venv`, tracked separately.)
- **Raise Qdrant client/server timeouts**: masks the symptom (a longer hang) without fixing the
  underlying I/O stall, and does nothing for the un-killable shutdown. Rejected.

## Consequences

- Qdrant storage is no longer a folder under the repo; it lives in the Docker-managed volume
  `qdrant_storage` (inspect via `docker volume inspect sb100_agents_qdrant_storage` or from inside
  the container). It is not browsable from Windows Explorer.
- The corpus must be (re)ingested into the fresh volume with `python scripts/ingest.py ./archives/`;
  the source PDFs under `archives/` are the source of truth, so no data is lost.
- The previously bind-mounted `./qdrant_storage/` directory (already gitignored) is now unused and
  can be deleted.
- Data persists across `docker compose up/down` and container recreation, but is tied to the Docker
  engine's volume store rather than the project directory; a deliberate `docker volume rm` (or
  `docker compose down -v`) clears it, after which re-ingestion restores the corpus.
