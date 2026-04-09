class Skill:
    """
    Base class for all S.P.A.R.K. Skills.
    Skills must implement the execute method.
    """
    name: str = "BaseSkill"
    description: str = "A foundational skill."

    async def execute(self, **kwargs) -> dict:
        raise NotImplementedError("Skills must implement the execute method.")
