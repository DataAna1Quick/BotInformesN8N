from core.auth import hash_password, verify_password


def test_default_hash_matches_password():
    assert verify_password("QuickHelp2026") is True


def test_wrong_password_rejected():
    assert verify_password("wrong") is False
    assert verify_password("") is False
    assert verify_password("quickhelp2026") is False  # case sensitive


def test_round_trip_with_fresh_hash(monkeypatch):
    h = hash_password("Test123!")
    monkeypatch.setattr("core.auth.DEFAULT_PASSWORD_HASH", h)
    assert verify_password("Test123!") is True
    assert verify_password("Test1234!") is False
