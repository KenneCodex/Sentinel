# Magic Square Idler (engine scaffolding)

This folder defines the minimal audit-native scaffolding for a magic square idler game:
- versioned content pack (rulesets)
- versioned upgrade node graph (nodes + per-node costs)
- deterministic state hashing + 384-bin routing
- JSONL telemetry events
- bounded per-player bandit policy (arm selection only)

## Upgrade node graph

`data/msq/node_graph_v1.json` (schema: `schemas/msq_node_graph_v1.schema.json`)
defines the upgrade nodes and their unlock costs, denominated in `SE` (the idle
Spark Energy currency from the content pack):

| node_id | name | cost (SE) | requires |
| --- | --- | --- | --- |
| 1 | Foundation | 0 | — |
| 2 | Spark Yield I | 100 | 1 |
| 3 | Proximity Tuning | 250 | 2 |
| 4 | Combo Extender | 500 | 3 |
| 5 | Lock Discount | 1000 | 3 |

Non-goals:
- no UI
- no auto-patching or global rollout
- no sensitive inference
