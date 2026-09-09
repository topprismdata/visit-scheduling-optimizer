import json
from svc.hashing import canonical_json, sha256_of


def test_canonical_json_sorted_keys_and_stable():
    a = {"b": 1, "a": 2.0}
    b = {"a": 2.0, "b": 1}
    assert canonical_json(a) == canonical_json(b)


def test_canonical_json_float_truncation():
    a = {"x": 0.1234567890123}
    b = {"x": 0.1234567890124}   # 1e-9 内差异视为相同
    assert canonical_json(a) == canonical_json(b)


def test_sha256_of_deterministic():
    assert sha256_of({"a": 1}) == sha256_of({"a": 1})
    assert sha256_of({"a": 1}) != sha256_of({"a": 2})
    assert sha256_of({"a": 1}).startswith("sha256:")
