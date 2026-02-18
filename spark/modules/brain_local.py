
import asyncio
import ollama
import structlog
import time

logger = structlog.get_logger()

class LocalBrain:
    def __init__(self, model_name="llama3"):
        self.model = model_name
        self.is_healthy = False
        self._check_health()
    
    def _check_health(self):
        """Minimal startup check to see if Ollama is responsive."""
        try:
            # Simple list call is fast enough for initialization
            ollama.list() 
            self.is_healthy = True
            logger.info("local_brain_ready", model=self.model)
        except Exception as e:
            self.is_healthy = False
            logger.warning("local_brain_offline", error=str(e))
    
    async def warmup(self):
        """Pre-load model into memory to avoid first-token latency shock."""
        if not self.is_healthy: return
        
        try:
            logger.info("local_brain_warming_up")
            # Empty prompt forces model load
            await asyncio.to_thread(ollama.generate, model=self.model, prompt="") 
            logger.info("local_brain_warm")
        except Exception:
            pass

    async def think_stream(self, prompt):
        """
        Yields chunks from local model.
        Metrics: First Token Latency, Total Time.
        """
        if not self.is_healthy:
            yield "[System: Local Brain is Offline. Check Ollama.]"
            return

        start_time = time.time()
        first_token_time = None
        
        try:
            # Offload blocking generator to thread
            stream = await asyncio.to_thread(
                ollama.chat, 
                model=self.model, 
                messages=[{'role': 'user', 'content': prompt}], 
                stream=True
            )
            
            for chunk in stream:
                content = chunk['message']['content']
                if content:
                    if first_token_time is None:
                        first_token_time = time.time()
                        latency = (first_token_time - start_time) * 1000
                        logger.debug("local_brain_first_token", ms=int(latency))
                    
                    yield content
                    
            total_time = (time.time() - start_time) * 1000
            logger.info("local_brain_complete", ms=int(total_time))
            
        except Exception as e:
            logger.error("local_brain_failed", error=str(e))
            self.is_healthy = False # Mark unhealthy on crash
            yield f"[System: Local Brain Crash - {e}]"

# Global Instance
local_brain = LocalBrain()
