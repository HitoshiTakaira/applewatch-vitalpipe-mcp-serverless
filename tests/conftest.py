from __future__ import annotations

import boto3
import pytest
from moto import mock_aws

from health_mcp import dynamo

TEST_TABLE_NAME = "test-health-data"
TEST_SECRET_PARAMETER_NAME = "/health-mcp/shared-secret"
TEST_SECRET_VALUE = "test-secret-value"


@pytest.fixture(autouse=True)
def aws_credentials(monkeypatch):
    """Dummy credentials so boto3 never accidentally reaches real AWS."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


@pytest.fixture
def dynamodb_table(monkeypatch):
    monkeypatch.setenv("DYNAMODB_TABLE_NAME", TEST_TABLE_NAME)
    with mock_aws():
        client = boto3.client("dynamodb", region_name="us-east-1")
        client.create_table(
            TableName=TEST_TABLE_NAME,
            AttributeDefinitions=[
                {"AttributeName": "pk", "AttributeType": "S"},
                {"AttributeName": "sk", "AttributeType": "S"},
            ],
            KeySchema=[
                {"AttributeName": "pk", "KeyType": "HASH"},
                {"AttributeName": "sk", "KeyType": "RANGE"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        # dynamo.get_table() caches its Table at module scope; clear it so the
        # cache doesn't hold a handle bound to a previous test's mock_aws().
        dynamo._table = None
        yield
        dynamo._table = None


@pytest.fixture
def ssm_secret(monkeypatch):
    monkeypatch.setenv("SECRET_PARAMETER_NAME", TEST_SECRET_PARAMETER_NAME)
    with mock_aws():
        client = boto3.client("ssm", region_name="us-east-1")
        client.put_parameter(
            Name=TEST_SECRET_PARAMETER_NAME,
            Value=TEST_SECRET_VALUE,
            Type="SecureString",
        )

        from handlers.authorizer import app as authorizer_app

        authorizer_app._secret_cache = None
        authorizer_app._ssm = None
        yield TEST_SECRET_VALUE
        authorizer_app._secret_cache = None
        authorizer_app._ssm = None
