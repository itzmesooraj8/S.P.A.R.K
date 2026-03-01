"""
Intelligence Agent — globe event analysis, geopolitical reasoning, threat assessment.
"""
from agents.base_agent import BaseAgent, AgentTask, AgentResult
from llm.model_router import model_router, TaskType, LatencyClass


class IntelligenceAgent(BaseAgent):
    name = "intelligence_agent"
    description = "Globe event analysis, geopolitical intelligence, threat briefings"
    capabilities = ["intel", "geopolitical", "threat_brief", "event_analysis", "conflict_analysis"]

    async def execute(self, task: AgentTask) -> AgentResult:
        events   = task.payload.get("events", [])
        region   = task.payload.get("region", "global")
        focus    = task.payload.get("focus", "general threat assessment")
        raw_data = task.payload.get("raw_data", "")

        system_prompt = (
            "You are SPARK's Intelligence Analysis Agent. "
            "You process real-world event data and produce structured geopolitical intelligence briefings. "
            "Format output as: SITUATION SUMMARY → KEY ACTORS → THREAT VECTORS → RISK LEVEL (LOW/MED/HIGH/CRITICAL) → RECOMMENDED MONITORING."
        )

        if events:
            events_str = "\n".join(f"- {e}" for e in events[:20])
            user_text = (
                f"Analyze these recent events in [{region}]:\n{events_str}\n\n"
                f"Intelligence focus: {focus}"
            )
        elif raw_data:
            user_text = f"Analyze this intelligence data for [{region}]:\n{raw_data}\n\nFocus: {focus}"
        else:
            user_text = f"Provide a current threat assessment for: {region}. Focus: {focus}"

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
                confidence=0.70,
            )
        except Exception as exc:
            return AgentResult(
                task_id=task.task_id, agent_name=self.name,
                success=False, output=None, error=str(exc),
            )
