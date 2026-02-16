# Magic Square Idler (engine scaffolding)

This folder defines the minimal audit-native scaffolding for a magic square idler game:
- versioned content pack (rulesets)
- deterministic state hashing + 384-bin routing
- JSONL telemetry events
- bounded per-player bandit policy (arm selection only)

Non-goals:
- no UI
- no auto-patching or global rollout
- no sensitive inference
