import asyncio

from sqlalchemy import event

from app.db import engine
from app.schema import schema


async def run(query: str, ctx, variables=None):
    result = await schema.execute(query, variable_values=variables, context_value=ctx)
    assert result.errors is None, result.errors
    return result.data


PAGE = """
query($after: String, $filter: IncidentFilter) {
  incidents(first: 3, after: $after, filter: $filter) {
    totalCount
    pageInfo { hasNextPage endCursor }
    edges { cursor node { id title } }
  }
}
"""


async def test_cursor_pagination_walks_every_row_once_newest_first(ctx):
    seen, after = [], None
    while True:
        data = (await run(PAGE, ctx, {"after": after}))["incidents"]
        seen += [e["node"]["id"] for e in data["edges"]]
        if not data["pageInfo"]["hasNextPage"]:
            break
        after = data["pageInfo"]["endCursor"]
    assert seen == ["7", "6", "5", "4", "3", "2", "1"]


async def test_filters_compose(ctx):
    data = await run(
        PAGE, ctx, {"filter": {"status": ["INVESTIGATING"], "severity": ["SEV1"], "search": "incident"}}
    )
    assert data["incidents"]["totalCount"] == 1
    assert data["incidents"]["edges"][0]["node"]["id"] == "7"


async def test_bad_cursor_is_a_graphql_error(ctx):
    result = await schema.execute(PAGE, variable_values={"after": "nope"}, context_value=ctx)
    assert result.errors and "Invalid cursor" in result.errors[0].message


async def test_nested_fields_are_batched_not_n_plus_one(ctx):
    statements: list[str] = []

    def count(conn, cursor, statement, *_):
        statements.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", count)
    try:
        await run(
            "{ incidents(first: 7) { edges { node { service { name openIncidentCount } updates { message } } } } }",
            ctx,
        )
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", count)
    # incidents page + count + services + open counts + updates = 5, regardless of row count
    assert len(statements) <= 5, statements


async def test_open_incident_validates_and_returns_union(ctx):
    mutation = """
    mutation($input: OpenIncidentInput!) {
      openIncident(input: $input) {
        __typename
        ... on IncidentType { id status updates { message } }
        ... on UserError { field message }
      }
    }"""
    bad = await run(mutation, ctx, {"input": {"serviceId": "1", "title": "  ", "severity": "SEV2", "message": "x"}})
    assert bad["openIncident"] == {"__typename": "UserError", "field": "title", "message": "Give the incident a title."}

    ok = await run(mutation, ctx, {"input": {"serviceId": "1", "title": "DB down", "severity": "SEV1", "message": "Pager fired"}})
    assert ok["openIncident"]["__typename"] == "IncidentType"
    assert ok["openIncident"]["status"] == "INVESTIGATING"
    assert ok["openIncident"]["updates"] == [{"message": "Pager fired"}]


async def test_resolving_sets_timestamp_and_blocks_further_updates(ctx):
    mutation = """
    mutation($input: PostUpdateInput!) {
      postUpdate(input: $input) {
        __typename
        ... on IncidentType { status resolvedAt }
        ... on UserError { message }
      }
    }"""
    resolved = await run(mutation, ctx, {"input": {"incidentId": "5", "status": "RESOLVED", "message": "Fixed"}})
    assert resolved["postUpdate"]["status"] == "RESOLVED"
    assert resolved["postUpdate"]["resolvedAt"].endswith("+00:00")

    again = await run(mutation, ctx, {"input": {"incidentId": "5", "status": "MONITORING", "message": "Oops"}})
    assert again["postUpdate"]["__typename"] == "UserError"


async def test_stats(ctx):
    data = await run("{ stats { openTotal openBySeverity { severity count } } }", ctx)
    assert data["stats"]["openTotal"] == 4
    assert {"severity": "SEV1", "count": 1} in data["stats"]["openBySeverity"]


async def test_subscription_receives_mutation_event(ctx):
    sub = await schema.subscribe("subscription { incidentChanged { id status } }", context_value=ctx)

    async def mutate():
        await asyncio.sleep(0.05)
        await schema.execute(
            'mutation { postUpdate(input: {incidentId: "4", status: IDENTIFIED, message: "Found it"}) { __typename } }',
            context_value=ctx,
        )

    task = asyncio.create_task(mutate())
    first = await asyncio.wait_for(anext(sub), timeout=3)
    await task
    await sub.aclose()
    assert first.data == {"incidentChanged": {"id": "4", "status": "IDENTIFIED"}}
