# MiniBench precommitted autonomy envelope

## Why this exists

Metaculus FutureEval prize rules require prize-eligible bots to operate with **no human in the loop while forecasting**. Human review of an active-question bot output followed by tuning is therefore incompatible with the current per-forecast approval model in PR #48.

This successor slice does **not** enable autonomous publishing. It only validates the authority envelope that would have to exist *before* a competition run can begin.

## Current MiniBench target

- Tournament reference: `minibench`
- Public series: MiniBench
- Current round: September 7–25, 2026
- Public prize pool: $1,000
- Public question count at round start: 60

The Metaculus reference bot uses `CURRENT_MINIBENCH_ID = "minibench"`.

## Governance model

The human may authorize a bounded competition run before the bot sees or produces active-question forecasts. Once the run begins, the following are fixed until the envelope expires or the process stops:

- tournament reference;
- time window;
- maximum number of forecasts;
- allowed Metaculus host;
- allowed external write classes;
- requirement to post a reasoning comment with each forecast;
- prohibition on live human forecast review and live tuning.

The envelope validator intentionally performs no network access and does not read `METACULUS_TOKEN`.

## Fail-closed predicates

A valid envelope must require all of the following:

- schema `sentinel.metaculus.autonomy-envelope/0.1`;
- competition and tournament reference exactly `minibench`;
- a non-placeholder human precommit authority ID;
- active, timezone-aware UTC validity window;
- a bounded positive `max_forecasts` no greater than 100;
- `require_reasoning_comment=true`;
- `human_in_loop_during_forecasting=false`;
- `allow_live_tuning=false`;
- `allow_forecast_preview_to_human=false`;
- allowed write methods exactly `forecast` and `comment`;
- allowed network hosts exactly `www.metaculus.com`.

Any mismatch blocks activation.

## Validate an envelope

Copy the example envelope, replace the placeholder authority ID, set a deliberately bounded validity window, and run:

```bash
python -m tools.futureeval_envelope path/to/envelope.json \
  --receipt receipts/minibench-envelope.json
```

The receipt contains the canonical envelope SHA-256 and explicitly records that no network or credential access occurred.

## Activation remains HOLD

A valid envelope is **necessary but not sufficient** to start a prize-eligible run.

Before any autonomous publish mode can be enabled, a follow-on implementation must demonstrate all of these gates:

1. Node 2 / AEON clean runtime placement is evidenced.
2. `METACULUS_TOKEN` is provisioned only through the runtime secret mechanism.
3. Question discovery is scoped to `minibench`.
4. Every forecast is paired with a reasoning comment as required by Metaculus rules.
5. Forecast + comment failures are surfaced in receipts; partial submission states cannot be silently reported as success.
6. The active run cannot expose forecast candidates for human review before posting.
7. The active run cannot modify prompts, models, calibration policy, or forecast logic after active-question outputs have been generated.
8. The run stops at envelope expiry, forecast cap, scope mismatch, credential failure, API failure that cannot be safely reconciled, or explicit emergency stop.
9. No merge, competition registration, terms acceptance, credential provisioning, or external forecast submission is implied by this document.

## Relationship to PR #48

PR #48 remains the evidence-preserving READ/PREPARE implementation. It should stay unchanged while this stacked successor is reviewed. Its per-forecast `--approval-id` publish model remains suitable for ordinary non-competition consequential writes, but it is not sufficient for a prize-eligible no-human-in-the-loop MiniBench run.
