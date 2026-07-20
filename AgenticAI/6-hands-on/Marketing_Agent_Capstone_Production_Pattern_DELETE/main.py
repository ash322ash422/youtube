"""
main.py
--------
Entry point for the marketing campaign analysis pipeline.

Usage:
    python main.py                    # rule-based mode (no API key needed)
    python main.py --use-llm          # real Claude tool-calling in every agent
    python main.py --use-llm --reset  # ignore any previous checkpoint, start clean
    python main.py --auto-approve     # skip the human-approval prompt (useful for CI/demos)
"""

import argparse
import os

import config
from orchestrator import Orchestrator


def parse_args():
    parser = argparse.ArgumentParser(description="Marketing campaign analysis agent pipeline")
    parser.add_argument("--use-llm", action="store_true",
                         help="Use real Claude tool-calling instead of rule-based fallbacks")
    parser.add_argument("--reset", action="store_true",
                         help="Discard any existing checkpoint and start the pipeline from stage 1")
    parser.add_argument("--auto-approve", action="store_true",
                         help="Automatically approve any write action instead of prompting a human")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.auto_approve:
        os.environ["AUTO_APPROVE_ACTIONS"] = "true"
        config.AUTO_APPROVE_ACTIONS = True

    orchestrator = Orchestrator(use_llm=args.use_llm if args.use_llm else None)

    if args.reset:
        orchestrator.reset()

    report = orchestrator.run()
    print("\n" + report)

    print(
        "(Tip: inspect memory/ for what each agent remembers, and checkpoints/ "
        "for the orchestrator's resumable pipeline state. Run main.py again "
        "without --reset to see the pipeline resume instead of repeat completed work.)"
    )
