import asyncio
import functools
import time
import structlog
from typing import Callable, Any

logger = structlog.get_logger()

class CircuitBreakerOpenException(Exception):
    pass

def circuit_breaker(failure_threshold: int = 3, recovery_timeout: int = 60, fallback_function: Callable = None):
    """
    Decorator that implements the Circuit Breaker pattern.
    If the decorated function fails `failure_threshold` times, it 'opens' the circuit
    and raises CircuitBreakerOpenException (or calls fallback) for `recovery_timeout` seconds.
    """
    def decorator(func: Callable) -> Callable:
        # State stored in function attributes
        func.failures = 0
        func.last_failure_time = 0
        func.state = "CLOSED" # CLOSED (normal), OPEN (failing), HALF-OPEN (testing)

        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            now = time.time()

            # Check if circuit is OPEN
            if func.state == "OPEN":
                if now - func.last_failure_time > recovery_timeout:
                    func.state = "HALF-OPEN"
                    logger.info("circuit_breaker_half_open", function=func.__name__)
                else:
                    logger.warning("circuit_breaker_open", function=func.__name__, remaining_time=int(recovery_timeout - (now - func.last_failure_time)))
                    if fallback_function:
                        return await fallback_function(*args, **kwargs)
                    raise CircuitBreakerOpenException(f"Circuit OPEN for {func.__name__}")

            try:
                result = await func(*args, **kwargs)
                
                # Success resets the breaker
                if func.state == "HALF-OPEN":
                     logger.info("circuit_breaker_closed", function=func.__name__)
                
                func.failures = 0
                func.state = "CLOSED"
                return result

            except Exception as e:
                func.failures += 1
                func.last_failure_time = now
                logger.error("circuit_breaker_failure", function=func.__name__, failure_count=func.failures, error=str(e))

                if func.failures >= failure_threshold:
                    func.state = "OPEN"
                    logger.critical("circuit_breaker_tripped", function=func.__name__, timeout=recovery_timeout)
                
                # Should we raise the original error or the fallback?
                # Usually we raise the error so the caller knows, unless fallback handles it.
                if fallback_function and func.state == "OPEN":
                     return await fallback_function(*args, **kwargs)
                raise e

        return wrapper
    return decorator
