from handlers.authorizer.app import handler


def test_authorizer_valid_token(ssm_secret):
    event = {"headers": {"authorization": f"Bearer {ssm_secret}"}}

    assert handler(event, None) == {"isAuthorized": True}


def test_authorizer_wrong_token(ssm_secret):
    event = {"headers": {"authorization": "Bearer wrong-token"}}

    assert handler(event, None) == {"isAuthorized": False}


def test_authorizer_missing_header(ssm_secret):
    assert handler({"headers": {}}, None) == {"isAuthorized": False}


def test_authorizer_caches_secret_across_invocations(ssm_secret, monkeypatch):
    from handlers.authorizer import app as authorizer_app

    event = {"headers": {"authorization": f"Bearer {ssm_secret}"}}
    handler(event, None)
    assert authorizer_app._secret_cache == ssm_secret

    # A second invocation must not call SSM again: break get_parameter and
    # confirm the cached value is still used.
    def _boom(*args, **kwargs):
        raise AssertionError("get_parameter should not be called again")

    monkeypatch.setattr(authorizer_app._ssm, "get_parameter", _boom)
    assert handler(event, None) == {"isAuthorized": True}
