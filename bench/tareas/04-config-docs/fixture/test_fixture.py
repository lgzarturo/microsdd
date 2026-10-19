from fixture_mod import VERSION
def test_version_semver():
    parts = VERSION.split('.')
    assert len(parts) == 3
