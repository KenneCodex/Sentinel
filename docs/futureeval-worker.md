# FutureEval worker (DOS80211b0t)

This worker is a local-first Metaculus FutureEval integration for Sentinel. It is designed to prepare and validate candidate forecasts while preserving an explicit human authority boundary around external writes.

## Default posture

- Dry-run is the default.
- No credential is stored by the worker.
- Authenticated tournament discovery is GET-only.
- A forecast POST requires **all** of the following:
  1. `--publish`
  2. `SENTINEL_METACULUS_WRITE_APPROVED=1`
  3. a non-empty `--approval-id`
  4. `METACULUS_TOKEN` in the runtime environment
- Possession of a token is not authority to publish.
- The token must never be committed, written into receipts, or pasted into ordinary chat.

## Current target

The worker uses tournament ID `33022`, the Summer 2026 FutureEval tournament ID published in the official Metaculus bot template.

## Read-only discovery

Provision `METACULUS_TOKEN` through the node's secure environment mechanism, then run:

```bash
python -m tools.futureeval_worker --list-open
```

This operation performs an authenticated GET and prints the open question inventory. It does not submit forecasts.

## Candidate dry-run

```bash
python -m tools.futureeval_worker \
  --question-id 12345 \
  --probability-yes 0.42 \
  --receipt receipts/futureeval-candidate-12345.json
```

The receipt records the payload hash and `DRY_RUN_NO_WRITE`.

## Publish gate

Only after the exact candidate payload has been reviewed:

```bash
export SENTINEL_METACULUS_WRITE_APPROVED=1
python -m tools.futureeval_worker \
  --question-id 12345 \
  --probability-yes 0.42 \
  --publish \
  --approval-id 'HUMAN-REVIEW-...' \
  --receipt receipts/futureeval-submission-12345.json
```

`METACULUS_TOKEN` must already be present in the process environment. Do not place the token on the command line.

## Node 2 / AEON verification sequence

From a clean Sentinel checkout on the dedicated branch:

```bash
git rev-parse --show-toplevel
git status --porcelain=v1
git rev-parse HEAD
git branch --show-current
python -m pytest tests/test_futureeval_worker.py -q
python -m tools.futureeval_worker --question-id 12345 --probability-yes 0.42 --receipt receipts/futureeval-smoke.json
```

Expected pre-credential state:

- tests pass;
- dry-run receipt says `DRY_RUN_NO_WRITE`;
- `python -m tools.futureeval_worker --list-open` fails closed with `METACULUS_TOKEN is not present`;
- no network write occurs.

After the token is securely provisioned, run `--list-open` only. Do not enable publishing during the deployment-verification step.

## Current implementation boundary

The first slice supports binary forecast payloads, open-question discovery, authority checks, and receipts. Forecast research/scoring and additional question types remain separate follow-on work.
