"""
S.P.A.R.K. CLI Interface
Entry point for command-line interaction.
"""

import argparse
from spark.main import main

def run_cli():
    parser = argparse.ArgumentParser(description="S.P.A.R.K. Autonomous Agent")
    # Add CLI arguments here
    args = parser.parse_args()
    main()

if __name__ == "__main__":
    run_cli()
