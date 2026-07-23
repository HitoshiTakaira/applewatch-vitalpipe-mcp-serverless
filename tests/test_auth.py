from health_mcp.auth import extract_bearer_token, is_valid_token


def test_extract_bearer_token_case_insensitive_header_name():
    assert extract_bearer_token({"Authorization": "Bearer abc123"}) == "abc123"
    assert extract_bearer_token({"authorization": "Bearer abc123"}) == "abc123"


def test_extract_bearer_token_missing_header():
    assert extract_bearer_token({}) is None
    assert extract_bearer_token(None) is None


def test_extract_bearer_token_wrong_scheme():
    assert extract_bearer_token({"authorization": "Basic abc123"}) is None


def test_is_valid_token_match():
    assert is_valid_token("secret", "secret") is True


def test_is_valid_token_mismatch():
    assert is_valid_token("wrong", "secret") is False


def test_is_valid_token_none():
    assert is_valid_token(None, "secret") is False
