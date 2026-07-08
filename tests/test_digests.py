from faber.digests import sha256_digest


def test_digest_is_stable_and_prefixed() -> None:
    assert sha256_digest({"b": 2, "a": 1}) == sha256_digest({"a": 1, "b": 2})
    assert sha256_digest({"a": 1}).startswith("sha256:")


def test_digest_changes_when_meaningful_content_changes() -> None:
    assert sha256_digest({"accepted": True}) != sha256_digest({"accepted": False})
