import base64
import json

from handlers.ingest_function.app import handler
from health_mcp import dynamo


def _event(body: dict, *, base64_encode: bool = False) -> dict:
    raw = json.dumps(body)
    if base64_encode:
        return {"body": base64.b64encode(raw.encode()).decode(), "isBase64Encoded": True}
    return {"body": raw, "isBase64Encoded": False}


def _sample_payload() -> dict:
    return {
        "data": {
            "metrics": [
                {
                    "name": "active_energy",
                    "units": "kJ",
                    "data": [
                        {"date": "2026-07-19 08:00:00 +0900", "qty": 721.3, "source": "Apple Watch"}
                    ],
                }
            ],
            "workouts": [],
        }
    }


def test_ingest_valid_payload_writes_to_dynamo(dynamodb_table):
    response = handler(_event(_sample_payload()), None)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["ingested"] == 1
    assert body["skipped"] == 0

    items = list(
        dynamo.query_between("METRIC#active_energy", "2026-07-01T00:00:00Z", "2026-07-31T00:00:00Z")
    )
    assert len(items) == 1
    assert items[0]["unit"] == "kcal"


def test_ingest_base64_encoded_body(dynamodb_table):
    response = handler(_event(_sample_payload(), base64_encode=True), None)

    assert response["statusCode"] == 200
    assert json.loads(response["body"])["ingested"] == 1


def test_ingest_invalid_json_returns_400(dynamodb_table):
    response = handler({"body": "{not json", "isBase64Encoded": False}, None)

    assert response["statusCode"] == 400
    assert "error" in json.loads(response["body"])


def test_ingest_missing_data_key_returns_400(dynamodb_table):
    response = handler(_event({"unexpected": "shape"}), None)

    assert response["statusCode"] == 400


def test_ingest_unknown_unit_is_skipped_not_stored(dynamodb_table):
    payload = _sample_payload()
    payload["data"]["metrics"][0]["units"] = "cal"  # not a unit we know how to normalize

    response = handler(_event(payload), None)

    body = json.loads(response["body"])
    assert body["ingested"] == 0
    assert body["skipped"] == 1

    items = list(
        dynamo.query_between("METRIC#active_energy", "2026-07-01T00:00:00Z", "2026-07-31T00:00:00Z")
    )
    assert items == []
