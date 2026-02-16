# 384 Bin Harness

Deterministic 384-bin routing and distribution diagnostics for testing the “void as topology” hypothesis.

## Canonical contract

```text
CANON|v1|<dataset_id>|bin_harness_384|TRIPLET|<payload>
```

- `id = sha256(canonical_string)`
- `bin = int(id, 16) % 384`

## Metrics emitted per run

- `bin_counts[384]` (optional with `--include-counts`)
- `empty_bins`, `empty_ratio`
- `entropy` (Shannon)
- `gini`
- `max_load`
- `collision_bins` (counts >= 2)
- `top_bins` (bin + load + member IDs)

## Output files

- JSONL audit log: `audit/bin_harness/runs.jsonl`
- Last-run summary: `audit/bin_harness/summaries/latest.json`

## Usage

### Random control

```bash
python tools/bin_harness_384.py random --alphabet-file data/hebrew_22.txt --n 72 --runs 200 --seed 12345 --dataset-id RANDOM_CONTROL_HEB72
```

### Exhaustive 22 choose 3 lane

```bash
python tools/bin_harness_384.py exhaustive --alphabet-file data/hebrew_22.txt --dataset-id HEB_ALL_TRIPLETS_22C3 --include-counts
```

### Observed subset from file

```bash
python tools/bin_harness_384.py file --dataset-id HEB72_TRIPLET_GRID --input data/heb72_triplets.txt --include-counts
```

## Interpretation policy

Void-significance claims remain hypotheses until observed subset metrics are statistically distinct from random controls by one declared standard (for example, fixed p-value or sigma threshold).
