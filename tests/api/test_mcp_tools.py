"""P6-5: GET /api/v1/mcp/tools lists every registered tool with its approval flag."""

URL = "/api/v1/mcp/tools"
APPROVAL = {"reset_demo_setting", "create_refund_request"}


def test_unauthenticated_gets_401(client):
    assert client.get(URL).status_code == 401


def test_viewer_can_list_tools(client, viewer_headers):
    response = client.get(URL, headers=viewer_headers)
    assert response.status_code == 200
    tools = response.json()["tools"]
    assert len(tools) == 9
    for tool in tools:
        assert set(tool) == {"name", "description", "requires_approval"}
        assert tool["description"]


def test_approval_flags_match_the_policy(client, viewer_headers):
    tools = {t["name"]: t for t in client.get(URL, headers=viewer_headers).json()["tools"]}
    assert {n for n, t in tools.items() if t["requires_approval"]} == APPROVAL
    assert {"get_customer", "search_docs", "update_ticket", "create_escalation"} <= set(tools)
