from faber.canonical_json import canonical_json


def test_canonical_json_is_stable_across_key_order_changes() -> None:
    left = {"b": 2, "a": {"z": 3, "y": [2, 1]}}
    right = {"a": {"y": [2, 1], "z": 3}, "b": 2}

    assert canonical_json(left) == canonical_json(right)
    assert canonical_json(left) == '{"a":{"y":[2,1],"z":3},"b":2}'
