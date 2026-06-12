"""
Spark Observability — Production Monitoring

Metrics, Tracing, Audit Logs, Performance Monitoring

Questions you should always be able to answer:
- Why did SPARK do this?
- What agent made the decision?
- How long did it take?
- Why did it fail?
"""

from spark.observability.metrics import MetricsCollector
from spark.observability.tracer import Tracer
from spark.observability.audit import AuditLogger

__all__ = ["MetricsCollector", "Tracer", "AuditLogger"]
