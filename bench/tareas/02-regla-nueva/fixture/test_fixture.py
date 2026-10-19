from fixture_mod import eligible
def test_eligible():
    assert eligible(18) is True
    assert eligible(17) is False
