
import asyncio
import structlog
import time
# FIX: Import module instead of function for better testability (monkeypatching)
import spark.modules.brain as cloud_brain
from spark.modules.brain_local import local_brain

logger = structlog.get_logger()

# Circuit Breaker Config
MAX_FAILURES = 3
COOLDOWN_SECONDS = 60

class BrainManager:
    def __init__(self):
        self.mode = "secondary_fallback" # "primary" (Cloud), "fallback" (Local)
        self.cloud_failures = 0
        self.last_failure_time = 0
        self.cloud_status = "HEALTHY" # HEALTHY, UNSTABLE, DEAD
        
    async def warmup(self):
        """Prepare local fallback in background."""
        await local_brain.warmup()

    def _should_retry_cloud(self):
        """Check provided cooldown has passed."""
        if self.cloud_status == "HEALTHY":
            return True
        
        # If UNSTABLE, check timer
        if time.time() - self.last_failure_time > COOLDOWN_SECONDS:
            logger.info("brain_manager_retry_cloud")
            self.cloud_status = "HEALTHY" # Optimistic reset
            self.cloud_failures = 0
            return True
            
        return False

    async def think(self, user_question):
        """
        Smart Router:
        1. Try Cloud (if healthy/retry).
        2. On Catch -> Failover to Local.
        3. Yield Steam.
        """
        
        # --- Attempt 1: Cloud ---
        if self._should_retry_cloud():
            try:
                # We iterate the generator. If it crashes during iteration, we catch it.
                # FIX: Use module reference
                async for chunk in cloud_brain.think_stream(user_question):
                    yield chunk
                
                # If we finished successfully:
                return 

            except Exception as e:
                self.cloud_failures += 1
                self.last_failure_time = time.time()
                logger.warning("brain_manager_cloud_fail", error=str(e), count=self.cloud_failures)
                
                if self.cloud_failures >= MAX_FAILURES:
                    self.cloud_status = "UNSTABLE"
                    logger.warning("brain_manager_circuit_open", timeout=COOLDOWN_SECONDS)

        # --- Attempt 2: Local Fallback ---
        logger.info("brain_manager_using_local")
        yield "[System: Switched to Local Backup]\n"
        
        try:
             async for chunk in local_brain.think_stream(user_question):
                 yield chunk
        except Exception as e:
             logger.critical("brain_manager_total_failure", error=str(e))
             yield "[System: Critical Intelligence Failure. All brains offline.]"

# Global Instance
brain_manager = BrainManager()
