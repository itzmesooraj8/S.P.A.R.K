"""
Spark Orchestration — Execution Layer

ONLY responsible for execution:
- Agent Coordination
- Workflow Execution
- Tool Calling
- Scheduling
- Event Routing

No memory. No personality. No reasoning.
"""

from spark.orchestration.workflow import WorkflowEngine
from spark.orchestration.scheduler import TaskScheduler
from spark.orchestration.tool_executor import ToolExecutor

__all__ = ["WorkflowEngine", "TaskScheduler", "ToolExecutor"]
