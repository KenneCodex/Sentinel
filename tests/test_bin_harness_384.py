import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from tools.bin_harness_384 import canonical_string, gini_coefficient, route_bin, shannon_entropy


def test_entropy_zero_for_single_bin_mass():
    counts = [10] + [0] * 383
    assert abs(shannon_entropy(counts) - 0.0) < 1e-12


def test_entropy_uniform_equals_log_bin_count():
    counts = [1] * 384
    assert abs(shannon_entropy(counts) - math.log(384)) < 1e-12


def test_gini_zero_for_uniform_distribution():
    counts = [3] * 384
    assert abs(gini_coefficient(counts) - 0.0) < 1e-12


def test_route_bin_stable_for_same_input():
    canon = canonical_string("HEB72_TRIPLET_GRID", "bin_harness_384", "TRIPLET", "א-ב-ג")
    first_id, first_bin = route_bin(canon, 384)
    second_id, second_bin = route_bin(canon, 384)

    assert first_id == second_id
    assert first_bin == second_bin
    assert 0 <= first_bin < 384
