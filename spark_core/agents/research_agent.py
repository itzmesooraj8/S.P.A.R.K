"""
Research Agent — OSINT, web search, summarization, document retrieval.
"""
import uuid
from agents.base_agent import BaseAgent, AgentTask, AgentResult
from llm.model_router import model_router, TaskType, LatencyClass


class ResearchAgent(BaseAgent):
    name = "research_agent"
    description = "OSINT, web search, news summarization, document retrieval"
    capabilities = ["research", "search", "summarize", "news", "osint"]

    async def execute(self, task: AgentTask) -> AgentResult:
        query = task.payload.get("query", "")
        context = task.payload.get("context", "")

        system_prompt = (
            "You are SPARK's Research Intelligence Agent. "
            "Your role: find, extract, and synthesize information from provided sources. "
            "Be concise, accurate, and cite sources when available. "
            "Return structured intelligence: KEY FINDINGS, ANALYSIS, CONFIDENCE."
        )
        user_text = f"Research task: {query}\n\nContext:\n{context}" if context else f"Research task: {query}"

        output_tokens: list[str] = []
        try:
            async for token in model_router.route_generate(
                system_prompt, user_text,
                task_type=TaskType.SEARCH,
                latency_class=LatencyClass.BACKGROUND,
                context_tokens=len(user_text) // 4,
            ):
                output_tokens.append(token)

            full_output = "".join(output_tokens)
            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                success=True,
                output=full_output,
                confidence=0.75,
            )
        except Exception as exc:
            return AgentResult(
                task_id=task.task_id, agent_name=self.name,
                success=False, output=None, error=str(exc),
            )
