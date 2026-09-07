# MiniBench forecast + reasoning transaction receipts

This slice defines the transaction semantics needed before Sentinel can safely wire a live MiniBench transport.

## External API shape being modeled

The official Metaculus API exposes separate write endpoints for forecasts and comments:

- `POST /api/questions/forecast/`
- `POST /api/comments/create/`

The official no-framework Metaculus bot template posts a reasoning comment with:

```json
{
  "text": "<bot-generated reasoning>",
  "parent": null,
  "included_forecast": true,
  "is_private": true,
  "on_post": 456
}
```

The forecast and comment are two distinct external writes. They must therefore never be treated as an atomic write that either wholly happened or wholly did not.

## Current safety boundary

`tools/futureeval_transaction.py` performs **no network access** and reads **no credentials**. It cannot submit a forecast or comment.

It does three things only:

1. validates the already-precommitted MiniBench autonomy envelope;
2. prepares and hashes the forecast and mandatory reasoning-comment payloads;
3. classifies deterministic step results for a future transport adapter.

The command-line interface always emits `DRY_RUN_NO_WRITE` for a valid prepared transaction.

## Transaction states

### `DRY_RUN_NO_WRITE`

No external step was attempted. Both payload hashes are bound to the envelope receipt.

### `FORECAST_FAILED_NO_COMMENT_ATTEMPT`

The forecast step was attempted and did not succeed. The comment must not be attempted. A later authorized transport may retry the full transaction only after reconciling external reality.

### `FORECAST_ONLY_PARTIAL_WRITE`

The forecast succeeded but the reasoning comment either failed or was not attempted. This is an externally consequential partial state. The only safe retry scope is `comment_only`; blindly reposting the forecast could duplicate or alter external state.

### `COMPLETE_EXTERNAL_WRITE`

Both forecast and reasoning comment succeeded. Retry scope is `none`.

Impossible narratives are rejected. For example, a successful comment cannot be recorded if the forecast was never attempted or if the forecast failed.

## Bound fields

Each prepared transaction binds:

- precommit `authority_id`;
- autonomy-envelope SHA-256;
- forecast ordinal, which must stay within `max_forecasts`;
- Metaculus question ID and post ID;
- forecast payload SHA-256;
- reasoning-comment payload SHA-256;
- expected forecast and comment endpoint classes.

No token, raw external response body, or secret is written to a receipt.

## Follow-on gate

A later PR may add a production transport adapter only after all of these are satisfied:

1. PR #49 autonomy-envelope semantics remain valid.
2. Node 2 / AEON exact-head runtime evidence exists.
3. Current MiniBench rules and API behavior are reconfirmed.
4. Secure runtime credential provisioning is complete.
5. The transport records the forecast response before attempting the comment.
6. Partial failure cannot silently retry the forecast.
7. A one-time human precommit explicitly authorizes the bounded autonomous run before active-question outputs are generated.

Until then, this layer is evidence and state-machine preparation only.
