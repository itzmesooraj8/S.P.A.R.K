from dependency_injector import containers, providers
from core.config import settings
from spark.modules.memory import memory_engine  # Existing memory engine
from spark.vision.describer import VisionDescriber
from tools.registry import tool_registry

class Container(containers.DeclarativeContainer):
    
    config = providers.Configuration()
    config.from_pydantic(settings)

    # Core Services
    memory_service = providers.Singleton(
        lambda: memory_engine  # Wrap existing global for now
    )

    vision_service = providers.Singleton(
        VisionDescriber,
        model_name=config.vision.model
    )

    tool_registry_service = providers.Singleton(
        lambda: tool_registry
    )

    # Brain Service (Lazy loading to avoid circular imports)
    brain_service = providers.Singleton(
        "spark.modules.brain.StreamingBrain",
        memory=memory_service,
        tools=tool_registry_service
    )

container = Container()
