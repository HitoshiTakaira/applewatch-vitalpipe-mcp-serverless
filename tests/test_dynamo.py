from decimal import Decimal

from health_mcp import dynamo


def test_put_items_then_query_between(dynamodb_table):
    dynamo.put_items(
        [
            {
                "pk": "METRIC#active_energy",
                "sk": "2026-07-01T00:00:00Z",
                "value": Decimal("1"),
                "unit": "kcal",
            },
            {
                "pk": "METRIC#active_energy",
                "sk": "2026-07-02T00:00:00Z",
                "value": Decimal("2"),
                "unit": "kcal",
            },
            {
                "pk": "METRIC#active_energy",
                "sk": "2026-07-10T00:00:00Z",
                "value": Decimal("3"),
                "unit": "kcal",
            },
            {
                "pk": "METRIC#step_count",
                "sk": "2026-07-01T00:00:00Z",
                "value": Decimal("100"),
                "unit": "count",
            },
        ]
    )

    items = list(
        dynamo.query_between("METRIC#active_energy", "2026-07-01T00:00:00Z", "2026-07-05T00:00:00Z")
    )

    assert {item["sk"] for item in items} == {"2026-07-01T00:00:00Z", "2026-07-02T00:00:00Z"}


def test_put_items_is_idempotent_on_pk_sk(dynamodb_table):
    item = {
        "pk": "METRIC#active_energy",
        "sk": "2026-07-01T00:00:00Z",
        "value": Decimal("1"),
        "unit": "kcal",
    }
    dynamo.put_items([item])
    dynamo.put_items([{**item, "value": Decimal("999")}])

    items = list(
        dynamo.query_between("METRIC#active_energy", "2026-07-01T00:00:00Z", "2026-07-01T00:00:00Z")
    )

    assert len(items) == 1
    assert items[0]["value"] == Decimal("999")


def test_query_between_paginates_across_pages(dynamodb_table):
    items = [
        {
            "pk": "METRIC#active_energy",
            "sk": f"2026-07-{day:02d}T00:00:00Z",
            "value": Decimal(str(day)),
            "unit": "kcal",
        }
        for day in range(1, 21)
    ]
    dynamo.put_items(items)

    results = list(
        dynamo.query_between(
            "METRIC#active_energy",
            "2026-07-01T00:00:00Z",
            "2026-07-20T00:00:00Z",
            page_size=5,
        )
    )

    assert len(results) == 20
    assert {r["sk"] for r in results} == {i["sk"] for i in items}
