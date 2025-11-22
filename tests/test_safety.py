from smart_buddy.safety import moderate_text


def test_disallowed_violence():
    text = "I will kill you"
    res = moderate_text(text)
    assert isinstance(res, dict)
    assert not res["allowed"]
    assert any(r.startswith("disallowed_keyword:violence") for r in res["reasons"])
    assert res["category"] in ("violence", None) or "violence" in (
        res.get("category") or ""
    )


def test_pii_detection_email():
    text = "Contact me at test@example.com for details"
    res = moderate_text(text)
    assert isinstance(res, dict)
    assert not res["allowed"]
    assert any(r.startswith("pii_detected:email") for r in res["reasons"]) or any(
        m.get("type") == "pii" for m in res["details"].get("matches", [])
    )


def test_allowlist_allows_keyword():
    text = "This is porn and should be skipped by allowlist"
    # If 'porn' is in allowlist it should not cause blocking
    res = moderate_text(text, allowlist=["porn"])
    assert isinstance(res, dict)
    # should be allowed because the single disallowed token was allowlisted
    assert res["allowed"]
