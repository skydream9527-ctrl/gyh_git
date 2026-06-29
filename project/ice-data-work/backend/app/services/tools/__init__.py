"""内置工具集。所有工具经 tool_runner 调度，带访问控制 + 降级。"""
from .registry import TOOL_REGISTRY, ToolSpec, run_tool, list_tools  # noqa: F401
