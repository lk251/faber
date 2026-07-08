import hmac
from hashlib import sha256

from faber.adapters.github.webhooks import parse_event, verify_github_signature
from faber.digests import sha256_digest


def test_github_webhook_signature_verification() -> None:
    body = b'{"action":"opened"}'
    signature = "sha256=" + hmac.new(b"secret", body, sha256).hexdigest()

    assert verify_github_signature("secret", body, signature)
    assert not verify_github_signature("wrong", body, signature)
    assert not verify_github_signature("secret", body, "sha1=abc")
    assert not verify_github_signature("secret", body, "sha256=not-hex")


def test_github_event_normalization_records_payload_digest() -> None:
    payload = {
        "action": "opened",
        "repository": {"full_name": "lk251/faber"},
        "issue": {"number": 2},
    }

    event = parse_event("issues", payload, delivery_id="delivery-1")

    assert event.event_name == "issues"
    assert event.action == "opened"
    assert event.delivery_id == "delivery-1"
    assert event.repository_full_name == "lk251/faber"
    assert event.raw_payload_digest == sha256_digest(payload)
