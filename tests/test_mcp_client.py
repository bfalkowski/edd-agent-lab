import json

from edd_agent_lab.integrations.mcp_client import EddMcpClient


def test_mcp_client_lists_tools() -> None:
    client = EddMcpClient()
    names = {tool["name"] for tool in client.list_tools()}
    assert "edd.run_eval_suite" in names
    assert "edd.publish_run" in names
    assert "edd.compare_runs" in names


def test_mcp_client_runs_eval_suite_locally() -> None:
    client = EddMcpClient()
    result = client.call_tool(
        "edd.run_eval_suite",
        {
            "agent": "customer-solution",
            "suite": "baseline",
            "agent_version": "v0-baseline",
        },
    )
    assert "run_id" in result
    assert "summary_path" in result


def test_invoke_mcp_tool_helper() -> None:
    from edd_agent_lab.integrations.mcp_client import invoke_mcp_tool

    payload = invoke_mcp_tool(
        "edd.compare_runs",
        json.dumps({"before_run_id": "a", "after_run_id": "b"}),
    )
    assert "before_run_id" in payload
