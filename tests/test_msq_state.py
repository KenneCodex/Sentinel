from tools.msq_state import MSQState, canonical_string, state_id_and_bin


def test_state_hash_stable():
    st = MSQState(
        size=3,
        target_sum=15,
        ruleset_id="RS-MSQ-0001",
        tiles=[8, 1, 6, 3, 5, 7, 4, 9, 2],
        locks=[False] * 9,
    )
    c1 = canonical_string(st)
    c2 = canonical_string(st)
    assert c1 == c2
    hid1, b1 = state_id_and_bin(st)
    hid2, b2 = state_id_and_bin(st)
    assert hid1 == hid2
    assert b1 == b2
    assert 0 <= b1 < 384
