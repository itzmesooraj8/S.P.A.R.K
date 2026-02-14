"""
S.P.A.R.K. (Strategic Projection & Analytical Resource Kernel)
Entry point for the autonomous agent.
"""

from spark.orchestration.engine import OrchestrationEngine

def main():
    engine = OrchestrationEngine()
    engine.run()

if __name__ == "__main__":
    main()
