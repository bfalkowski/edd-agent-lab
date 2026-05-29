import httpx

from edd_agent_lab.integrations.edd_client import LAB_PUBLISH_PATH, RUN_INGEST_PATH, HttpEDDClient
from edd_agent_lab.integrations.publish import PUBLISH_SCHEMA_VERSION


def test_run_ingest_path_is_generic_endpoint() -> None:
    assert RUN_INGEST_PATH == "/v1/integrations/runs/publish"
    assert LAB_PUBLISH_PATH == "/v1/integrations/lab/publish"


def test_http_client_publishes_envelope() -> None:
    envelope = {
        "schema_version": PUBLISH_SCHEMA_VERSION,
        "source": "edd-agent-lab",
        "run_id": "http-run",
        "agent": "customer_solution_agent",
        "agent_version": "v3-competency-model",
        "suite": "overfitting",
        "scenario_ids": ["healthcare_documentation"],
        "eval_summary": {"overall_score": 1.0},
        "failure_packet": None,
        "outputs": {},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == RUN_INGEST_PATH
        return httpx.Response(
            201,
            json={
                "platform_run_id": "11111111-1111-1111-1111-111111111111",
                "gate_status": "pass",
                "gate_explanation": "Lab overall score 100.0 meets pass threshold 70.0.",
            },
        )

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport, base_url="http://edd.test") as http_client:
        client = HttpEDDClient(base_url="http://edd.test")
        client._request = lambda method, path, json=None: http_client.request(  # type: ignore[method-assign]
            method, path, json=json
        ).json()
        result = client.publish_envelope(envelope)

    assert result["status"] == "published_http"
    assert result["platform_run_id"] == "11111111-1111-1111-1111-111111111111"
    assert result["gate_status"] == "pass"
    assert "pass threshold" in str(result["gate_explanation"])


def test_http_client_queues_on_http_error() -> None:
    envelope = {
        "schema_version": PUBLISH_SCHEMA_VERSION,
        "source": "edd-agent-lab",
        "run_id": "queue-on-error",
        "agent": "customer_solution_agent",
        "agent_version": "v1-discovery-graph",
        "suite": "overfitting",
        "scenario_ids": [],
        "eval_summary": {"overall_score": 0.4},
        "failure_packet": None,
        "outputs": {},
    }

    class FailingClient(HttpEDDClient):
        def _request(self, method: str, path: str, json: dict | None = None) -> dict:
            raise httpx.ConnectError("platform unavailable", request=httpx.Request("POST", "/"))

    client = FailingClient(base_url="http://edd.test")
    result = client.publish_envelope(envelope)
    assert result["status"] == "queued_after_http_error"
    assert "queue_path" in result
