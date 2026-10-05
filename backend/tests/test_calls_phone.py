"""Phone → customer keys for calls uploaded from the agent's phone (services/calls/ingest.py)."""
from app.services.calls.ingest import EXT_BY_MIME, phone_display, phone_hash, phone_key
from app.services.calls.contract import AUDIO_EXTS


def test_phone_key_spellings_agree():
    spellings = ["050-1234567", "0501234567", "501234567", "+972501234567", "972-50-123-4567", " 050 123 4567 "]
    assert {phone_key(s) for s in spellings} == {"501234567"}


def test_landline_and_junk():
    assert phone_key("03-1234567") == phone_key("+972-3-123-4567") == "31234567"
    assert phone_display("+972-3-123-4567") == "031234567"
    assert phone_key("0097250-1234567") == "501234567"
    assert phone_key("*2797") is None
    assert phone_key("") is None and phone_key(None) is None


def test_display_is_local_spelling():
    assert phone_display("+972501234567") == "0501234567"
    assert phone_display("501234567") == "0501234567"


def test_hash_matches_device_formula():
    # Android computes sha256(phone_key) the same way — keep these in lockstep.
    import hashlib
    assert phone_hash("501234567") == hashlib.sha256(b"501234567").hexdigest()


def test_every_mime_maps_to_a_gateway_ext():
    assert set(EXT_BY_MIME.values()) <= set(AUDIO_EXTS)
