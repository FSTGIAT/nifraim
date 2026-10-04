"""Policy numbers that production and נפרעים write differently must still pair."""
from app.services.comparison_service import _extract_policy_core, _policy_matches


def test_altshuler_fund_prefix_pairs_with_bare_account():
    assert _extract_policy_core("1025-44837481") == "44837481"
    assert _extract_policy_core("512-39671489") == "39671489"
    assert _policy_matches("44837481", "1025-44837481")


def test_yelin_suffix_pairs_with_bare_account():
    assert _extract_policy_core("71856447-927") == "71856447"
    assert _policy_matches("71856447", "71856447-927")


def test_existing_formats_unchanged():
    assert _extract_policy_core("2-001-123456-7") == "123456"   # 4-part production
    assert _extract_policy_core("44837481") == "44837481"
    assert _extract_policy_core("AB-123456") == "AB-123456"     # not all digits
    assert _extract_policy_core("12345-67890") == "12345-67890"  # no short code
    assert not _policy_matches("44837481", "1025-44837482")


def test_phoenix_three_part_pairs_with_four_part_production():
    assert _extract_policy_core("006-255-344165") == "344165"
    assert _policy_matches("1-255-344165-0", "006-255-344165")
    assert _policy_matches("006-204-092754", "006-204-092754")      # same 3-part still pairs
    assert not _policy_matches("1-255-344165-0", "006-255-344166")
