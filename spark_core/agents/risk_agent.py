"""
Risk Agent — multi-domain risk scoring, escalation detection, simulation.
"""
import json
from agents.base_agent import BaseAgent, AgentTask, AgentResult
from llm.model_router import model_router, TaskType, LatencyClass


_RISK_LEVELS = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}

_RISK_SYSTEM = (
    "You are SPARK's Risk Assessment Agent. "
    "Evaluate the provided scenario and return a precise JSON risk report. "
    "Output ONLY valid JSON with this schema:\n"
    '{"risk_level":"LOW|MEDIUM|HIGH|CRITICAL","score":0-100,'
    '"primary_risks":["..."],"escalation_triggers":["..."],'
    '"probability":0.0-1.0,"recommended_actions":["..."],'
    '"reasoning":"..."}'
)


class RiskAgent(BaseAgent):
    name = "risk_agent"
    description = "Multi-domain risk scoring, escalation detection, probability modeling"
    capabilities = ["risk_score", "risk_assess", "escalation", "simulate", "threat_model"]

    async def execute(self, task: AgentTask) -> AgentResult:
        scenario = task.payload.get("scenario", "")
        domain   = task.payload.get("domain", "general")
        context  = task.payload.get("context", "")

        user_text = (
            f"Domain: {domain}\n"
            f"Scenario: {scenario}\n"
            + (f"Context: {context}" if context else "")
        )

        output_tokens: list[str] = []
        try:
            async for token in model_router.route_generate(
                _RISK_SYSTEM, user_text,
                task_type=TaskType.SAFETY,
                latency_class=LatencyClass.BACKGROUND,
                context_tokens=len(user_text) // 4,
            ):
                output_tokens.append(token)

            raw = "".join(output_tokens).strip()

            # Parse JSON response
            try:
                # Extract JSON block if wrapped in markdown
                if "```" in raw:
                    raw = raw.split("```")[1].lstrip("json").strip()
                risk_data = json.loads(raw)
                score = risk_data.get("score", 50)
                confidence = min(risk_data.get("probability", 0.5) + 0.3, 1.0)
            except json.JSONDecodeError:
                risk_data = {"raw_output": raw, "parse_error": True}
                score = 50
                confidence = 0.4

            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                success=True,
                output=risk_data,
                reasoning=risk_data.get("reasoning", ""),
                confidence=confidence,
            )
        except Exception as exc:
            return AgentResult(
                task_id=task.task_id, agent_name=self.name,
                success=False, output=None, error=str(exc),
            )
