"""
Optimization Agent — system performance analysis, strategy recommendations,
configuration tuning, resource optimization.
"""
from agents.base_agent import BaseAgent, AgentTask, AgentResult
from llm.model_router import model_router, TaskType, LatencyClass


class OptimizationAgent(BaseAgent):
    name = "optimization_agent"
    description = "System performance analysis, strategy tuning, resource optimization"
    capabilities = ["optimize", "performance", "strategy", "tune", "diagnose"]

    async def execute(self, task: AgentTask) -> AgentResult:
        target   = task.payload.get("target", "system")
        metrics  = task.payload.get("metrics", {})
        goal     = task.payload.get("goal", "improve performance")
        context  = task.payload.get("context", "")

        system_prompt = (
            "You are SPARK's Optimization Agent. "
            "Analyze system metrics and produce concrete, prioritized optimization recommendations. "
            "Format: CURRENT STATE → BOTTLENECKS → RANKED ACTIONS (with expected impact) → QUICK WINS."
        )
        user_text = (
            f"Optimization target: {target}\n"
            f"Goal: {goal}\n"
            f"Metrics: {metrics}\n"
            + (f"Context: {context}" if context else "")
        )

        output_tokens: list[str] = []
        try:
            async for token in model_router.route_generate(
                system_prompt, user_text,
                task_type=TaskType.REASONING,
                latency_class=LatencyClass.BACKGROUND,
                context_tokens=len(user_text) // 4,
            ):
                output_tokens.append(token)

            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                success=True,
                output="".join(output_tokens),
                confidence=0.80,
            )
        except Exception as exc:
            return AgentResult(
                task_id=task.task_id, agent_name=self.name,
                success=False, output=None, error=str(exc),
            )
