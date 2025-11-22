from smart_buddy.prompting import PromptTemplate


def test_prompt_render_and_moderation_blocks():
    pt = PromptTemplate(system="System note", instruction_template="{instruction}")
    # instruction that triggers violence moderation
    r = pt.safe_render("I will kill him")
    assert isinstance(r, dict)
    assert "prompt" in r and "USER:" in r["prompt"]
    assert r["allowed"] is False
    assert (
        r.get("moderation")
        and r["moderation"].get("category") in ("violence", None)
        or any(
            rr.startswith("disallowed_keyword:violence")
            for rr in r["moderation"].get("reasons", [])
        )
    )


def test_prompt_render_allowlist_allows():
    pt = PromptTemplate(system="S", instruction_template="{instruction}")
    r = pt.safe_render("This contains porn but should be allowed", allowlist=["porn"])
    assert isinstance(r, dict)
    assert r["allowed"] is True
    assert "prompt" in r and "USER:" in r["prompt"]
