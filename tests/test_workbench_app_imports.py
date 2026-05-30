from __future__ import annotations


def test_reference_data_exports_workbench_helpers() -> None:
    from edd_agent_lab.ui import reference_data
    from edd_agent_lab.ui.constants import LAB_CONSOLE_PORT

    assert LAB_CONSOLE_PORT == 8502
    for name in (
        "graph_diff_rows",
        "graph_flow_summary",
        "load_graph_design_bundle",
        "list_reference_artifact_paths",
        "load_tool_binding_rows",
        "reference_overall_score",
    ):
        assert hasattr(reference_data, name), f"missing reference_data.{name}"
