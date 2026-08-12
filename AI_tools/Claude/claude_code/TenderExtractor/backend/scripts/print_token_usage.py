#!/usr/bin/env python
"""
Prints the LLM token usage recorded for every job in config.JOBS_DB
(job_flow_status.db), plus the grand total.

Usage (run from the backend/ directory):
    python -m scripts.print_token_usage
"""
import sys

from app.services import job_store


def main() -> int:
    jobs = job_store.all_jobs()

    if not jobs:
        print("No jobs recorded yet.")
        return 0

    for job in jobs:
        print("-" * 60)
        for key, value in job.items():
            print(f"{key}: {value}")

    print("-" * 60)
    print(f"Total token usage across {len(jobs)} job(s): {job_store.total_token_usage()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
