# Sentinel

This repository currently centers on automation/docs artifacts for the Sentinel ecosystem.

## Local parity baseline

To keep parity with the broader multi-service effort, local environments should use these environment variables (in `.env` or exported shell env):

- `CODEXJR_PORT=5051`
- `SENTINEL_PORT=5052`
- `ARCHIVIST_PORT=5053`
- `SHRINE_PORT=5054`
- `CODEX_PHASE="Phase XX"`

All services are expected to expose `GET /healthz` and return:

```json
{"status":"ok","service":"<ServiceName>","phase":"<Phase>","port":<PortNumber>}
```

## Script behavior

`sentinel_client_update.sh` now:

1. Loads `.env` values when present.
2. Logs local parity phase/ports.
3. Performs safer install checks when auto-installing `git`/`python3.10`.
4. Runs a localhost `/healthz` check on each of the four configured service ports (5051-5054) and validates response shape.

## Quick check

```bash
bash -n sentinel_client_update.sh
```
