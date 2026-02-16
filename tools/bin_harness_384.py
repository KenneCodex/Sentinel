#!/usr/bin/env python3
"""384-bin routing harness for void topology diagnostics."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
import unicodedata
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

DEFAULT_N_BINS = 384
DEFAULT_SCRIPT = "bin_harness_384"
DEFAULT_UNIT_TYPE = "TRIPLET"
DEFAULT_CANON_VERSION = "v1"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_text(text: str) -> str:
    return unicodedata.normalize("NFKC", text.strip())


def canonical_string(
    dataset_id: str,
    script: str,
    unit_type: str,
    payload: str,
    version: str = DEFAULT_CANON_VERSION,
) -> str:
    return f"CANON|{version}|{dataset_id}|{script}|{unit_type}|{normalize_text(payload)}"


def route_bin(canon: str, n_bins: int = DEFAULT_N_BINS) -> Tuple[str, int]:
    hashed = sha256_hex(canon)
    return hashed, int(hashed, 16) % n_bins


def shannon_entropy(counts: List[int]) -> float:
    total = sum(counts)
    if total == 0:
        return 0.0
    entropy = 0.0
    for count in counts:
        if count == 0:
            continue
        p_i = count / total
        entropy -= p_i * math.log(p_i)
    return entropy


def gini_coefficient(counts: List[int]) -> float:
    n = len(counts)
    if n < 2:
        return 0.0

    total = sum(counts)
    if total == 0.0:
        return 0.0

    # O(n log n) implementation is more efficient than O(n^2).
    sorted_counts = sorted(counts)

    # Using the formula for Gini coefficient based on sorted values:
    # G = (sum_i (2i - n + 1)x_i) / (n * sum_i x_i) for 0-indexed i.
    numerator = sum((2 * i - n + 1) * val for i, val in enumerate(sorted_counts))
    denominator = n * total

    return numerator / denominator


def ranked_bins(counts: List[int], k: int = 10) -> List[Tuple[int, int]]:
    items = list(enumerate(counts))
    items.sort(key=lambda x: (-x[1], x[0]))
    return items[:k]


@dataclass
class HarnessRun:
    schema_version: str
    run_id: str
    created_at: str

    dataset_id: str
    mode: str
    n_bins: int
    N: int

    empty_bins: int
    empty_ratio: float
    entropy: float
    gini: float
    max_load: int
    collision_bins: int

    top_bins: List[Dict[str, object]]
    bin_counts: Optional[List[int]] = None

    script: str = DEFAULT_SCRIPT
    unit_type: str = DEFAULT_UNIT_TYPE
    canon_version: str = DEFAULT_CANON_VERSION
    seed: Optional[int] = None


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, record: dict) -> None:
    ensure_parent_dir(path)
    with path.open("w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)


def append_jsonl(path: Path, record: dict) -> None:
    ensure_parent_dir(path)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_lines(path: Path) -> List[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    cleaned = [normalize_text(line) for line in lines]
    return [line for line in cleaned if line]


def parse_alphabet_file(path: Path) -> List[str]:
    alphabet = load_lines(path)
    if len(alphabet) < 3:
        raise ValueError("alphabet must contain at least 3 symbols")
    return alphabet


def generate_exhaustive_triplets(alphabet: List[str]) -> Iterable[str]:
    for a, b, c in combinations(alphabet, 3):
        yield f"{a}-{b}-{c}"


def generate_random_triplets(alphabet: List[str], n: int, rng: random.Random) -> Iterable[str]:
    if n < 0:
        raise ValueError("n must be >= 0")
    if len(alphabet) < 3:
        raise ValueError("alphabet must contain at least 3 symbols")

    for _ in range(n):
        a, b, c = rng.sample(alphabet, 3)
        tokens = sorted([normalize_text(a), normalize_text(b), normalize_text(c)])
        yield "-".join(tokens)


def compute_run(
    dataset_id: str,
    mode: str,
    payloads: Iterable[str],
    n_bins: int,
    include_counts: bool,
    seed: Optional[int],
    top_member_limit: int = 25,
) -> HarnessRun:
    counts = [0] * n_bins
    members: Dict[int, List[str]] = {}
    n_units = 0

    for payload in payloads:
        canon = canonical_string(
            dataset_id=dataset_id,
            script=DEFAULT_SCRIPT,
            unit_type=DEFAULT_UNIT_TYPE,
            payload=payload,
            version=DEFAULT_CANON_VERSION,
        )
        identifier, bin_index = route_bin(canon, n_bins=n_bins)
        counts[bin_index] += 1
        n_units += 1

        members.setdefault(bin_index, [])
        if len(members[bin_index]) < top_member_limit:
            members[bin_index].append(identifier)

    empty_bins = sum(1 for c in counts if c == 0)
    max_load = max(counts) if counts else 0

    top_bins: List[Dict[str, object]] = []
    for bin_index, count in ranked_bins(counts, k=10):
        top_bins.append(
            {
                "bin": bin_index,
                "count": count,
                "member_ids": members.get(bin_index, []),
            }
        )

    now_iso = utc_now_iso()
    run = HarnessRun(
        schema_version="bin_harness_run_v1",
        run_id=f"RUN-BIN384-{sha256_hex(f'{dataset_id}|{mode}|{now_iso}')[:12].upper()}",
        created_at=now_iso,
        dataset_id=dataset_id,
        mode=mode,
        n_bins=n_bins,
        N=n_units,
        empty_bins=empty_bins,
        empty_ratio=(empty_bins / n_bins if n_bins else 0.0),
        entropy=shannon_entropy(counts),
        gini=gini_coefficient(counts),
        max_load=max_load,
        collision_bins=sum(1 for c in counts if c >= 2),
        top_bins=top_bins,
        bin_counts=counts if include_counts else None,
        seed=seed,
    )
    return run


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="384-bin routing harness")
    sub = parser.add_subparsers(dest="mode", required=True)

    random_parser = sub.add_parser("random", help="random control run(s)")
    random_parser.add_argument("--alphabet-file", required=True)
    random_parser.add_argument("--n", required=True, type=int)
    random_parser.add_argument("--runs", type=int, default=1)
    random_parser.add_argument("--seed", type=int, default=0)
    random_parser.add_argument("--n-bins", type=int, default=DEFAULT_N_BINS)
    random_parser.add_argument("--out", type=str, default=".audit-logs/bin_harness/runs.jsonl")
    random_parser.add_argument("--summary", type=str, default=".audit-logs/bin_harness/summaries/latest.json")
    random_parser.add_argument("--include-counts", action="store_true")
    random_parser.add_argument("--dataset-id", type=str, default="")

    exhaustive_parser = sub.add_parser("exhaustive", help="all nC3 from alphabet")
    exhaustive_parser.add_argument("--alphabet-file", required=True)
    exhaustive_parser.add_argument("--n-bins", type=int, default=DEFAULT_N_BINS)
    exhaustive_parser.add_argument("--out", type=str, default=".audit-logs/bin_harness/runs.jsonl")
    exhaustive_parser.add_argument("--summary", type=str, default=".audit-logs/bin_harness/summaries/latest.json")
    exhaustive_parser.add_argument("--include-counts", action="store_true")
    exhaustive_parser.add_argument("--dataset-id", type=str, default="")

    file_parser = sub.add_parser("file", help="triplets from newline-delimited file")
    file_parser.add_argument("--input", required=True)
    file_parser.add_argument("--n-bins", type=int, default=DEFAULT_N_BINS)
    file_parser.add_argument("--out", type=str, default=".audit-logs/bin_harness/runs.jsonl")
    file_parser.add_argument("--summary", type=str, default=".audit-logs/bin_harness/summaries/latest.json")
    file_parser.add_argument("--include-counts", action="store_true")
    file_parser.add_argument("--dataset-id", type=str, default="")

    args = parser.parse_args(argv)

    if args.n_bins <= 0:
        print("--n-bins must be > 0", file=sys.stderr)
        return 2

    out_path = Path(args.out)
    summary_path = Path(args.summary)
    include_counts = bool(args.include_counts)
    latest: Optional[dict] = None

    if args.mode == "random":
        alphabet = parse_alphabet_file(Path(args.alphabet_file))
        if args.runs <= 0:
            print("--runs must be > 0", file=sys.stderr)
            return 2

        dataset_prefix = args.dataset_id.strip() or "RANDOM_CONTROL"
        for idx in range(args.runs):
            run_seed = args.seed + idx
            payloads = generate_random_triplets(alphabet, args.n, random.Random(run_seed))
            run = compute_run(
                dataset_id=f"{dataset_prefix}_N{args.n}_RUN{idx + 1}",
                mode="random",
                payloads=payloads,
                n_bins=args.n_bins,
                include_counts=include_counts,
                seed=run_seed,
            )
            latest = asdict(run)
            append_jsonl(out_path, latest)

    elif args.mode == "exhaustive":
        alphabet = parse_alphabet_file(Path(args.alphabet_file))
        dataset_id = args.dataset_id.strip() or "HEB_ALL_TRIPLETS_22C3"
        run = compute_run(
            dataset_id=dataset_id,
            mode="exhaustive",
            payloads=generate_exhaustive_triplets(alphabet),
            n_bins=args.n_bins,
            include_counts=include_counts,
            seed=None,
        )
        latest = asdict(run)
        append_jsonl(out_path, latest)

    elif args.mode == "file":
        dataset_id = args.dataset_id.strip()
        if not dataset_id:
            print("--dataset-id is required for file mode", file=sys.stderr)
            return 2

        run = compute_run(
            dataset_id=dataset_id,
            mode="file",
            payloads=load_lines(Path(args.input)),
            n_bins=args.n_bins,
            include_counts=include_counts,
            seed=None,
        )
        latest = asdict(run)
        append_jsonl(out_path, latest)

    if latest is None:
        print("No output generated", file=sys.stderr)
        return 1

    write_json(summary_path, latest)
    print(f"Wrote JSONL: {out_path}")
    print(f"Wrote summary: {summary_path}")
    print(
        json.dumps(
            {
                "dataset_id": latest["dataset_id"],
                "mode": latest["mode"],
                "N": latest["N"],
                "empty_ratio": latest["empty_ratio"],
                "entropy": latest["entropy"],
                "gini": latest["gini"],
                "max_load": latest["max_load"],
                "collision_bins": latest["collision_bins"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
