"""
Code Agent — code generation, review, debugging, refactoring.
"""
from agents.base_agent import BaseAgent, AgentTask, AgentResult
from llm.model_router import model_router, TaskType, LatencyClass


class CodeAgent(BaseAgent):
    name = "code_agent"
    description = "Code generation, debugging, refactoring, code review"
    capabilities = ["code", "debug", "refactor", "review", "explain_code", "generate_code"]

    async def execute(self, task: AgentTask) -> AgentResult:
        action   = task.payload.get("action", "generate")
        code     = task.payload.get("code", "")
        language = task.payload.get("language", "python")
        request  = task.payload.get("request", "")

        system_prompt = (
            f"You are SPARK's Code Intelligence Agent. Expert in {language}. "
            "When generating code: write production-quality, well-commented code. "
            "When reviewing: identify bugs, security issues, and performance problems. "
            "When refactoring: preserve functionality, improve clarity and efficiency. "
            "Always explain your reasoning briefly before the code."
        )
        if action == "review" and code:
            user_text = f"Review this {language} code:\n```{language}\n{code}\n```\nFocus on: {request or 'bugs, security, performance'}"
        elif action == "debug" and code:
            user_text = f"Debug this {language} code:\n```{language}\n{code}\n```\nProblem: {request}"
        elif action == "refactor" and code:
            user_text = f"Refactor this {language} code:\n```{language}\n{code}\n```\nGoal: {request or 'improve clarity and performance'}"
        else:
            user_text = request or f"Generate {language} code"

        output_tokens: list[str] = []
        try:
            async for token in model_router.route_generate(
                system_prompt, user_text,
                task_type=TaskType.CODE,
                latency_class=LatencyClass.BACKGROUND,
                context_tokens=len(user_text) // 4,
            ):
                output_tokens.append(token)

            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                success=True,
                output="".join(output_tokens),
                confidence=0.85,
            )
        except Exception as exc:
            return AgentResult(
                task_id=task.task_id, agent_name=self.name,
                success=False, output=None, error=str(exc),
            )
