"""
orchestrator.py
-----------------
INDUSTRY PATTERN: durable, resumable workflows.

A plain Python script that calls agent.run() in sequence has a real
production problem: if the process crashes after Stage 2 (say, the
AnalyticsAgent finishes but the machine dies before CopilotAgent runs),
you have to start the entire pipeline over from scratch -- including
re-calling the LLM for steps that already succeeded.

Real systems solve this with a durable workflow engine (e.g. Temporal,
AWS Step Functions, LangGraph) that checkpoints progress after each
step and can resume exactly where it left off. This file is a
deliberately small, dependency-free version of that same idea: after
every stage completes, its output is written to disk. On startup, the
orchestrator checks for an existing checkpoint and resumes from the
first *incomplete* stage instead of redoing finished work.

The pipeline shape itself is unchanged from earlier versions of this
project -- it's still SEQUENTIAL, not parallel:

    DataAgent  --->  AnalyticsAgent  --->  CopilotAgent

What's different here is that the orchestrator is now resilient to
crashes between stages, and every stage transition is logged.
"""

import json
import os

import config
from agents.data_agent import DataAgent
from agents.analytics_agent import AnalyticsAgent
from agents.copilot_agent import CopilotAgent
from logging_config import get_logger

STAGES = ["data", "analytics", "copilot", "done"]


class Orchestrator:

    def __init__(self, csv_path: str = config.CAMPAIGN_CSV_PATH, use_llm=None, run_id: str = "latest"):
        self.data_agent = DataAgent(csv_path, use_llm=use_llm)
        self.analytics_agent = AnalyticsAgent(use_llm=use_llm)
        self.copilot_agent = CopilotAgent(use_llm=use_llm)

        self.log = get_logger("Orchestrator")
        os.makedirs(config.CHECKPOINT_DIR, exist_ok=True)
        self.checkpoint_path = os.path.join(config.CHECKPOINT_DIR, f"{run_id}.json")

    # ---- checkpointing ----
    def _load_checkpoint(self) -> dict:
        if os.path.exists(self.checkpoint_path):
            with open(self.checkpoint_path) as f:
                return json.load(f)
        return {"completed_stage": None, "data_output": None, "analytics_output": None, "copilot_output": None}

    def _save_checkpoint(self, state: dict) -> None:
        with open(self.checkpoint_path, "w") as f:
            json.dump(state, f, indent=2, default=str)

    # ---- main entry point ----
    def run(self) -> str:
        state = self._load_checkpoint()
        self.log.info("pipeline starting", extra={"resuming_from": state["completed_stage"]})

        # Stage 1: DataAgent -- skip if a prior run already finished it
        if state["completed_stage"] is None:
            self.log.info("running stage: data")
            state["data_output"] = self.data_agent.run()
            state["completed_stage"] = "data"
            self._save_checkpoint(state)
        else:
            self.log.info("skipping stage: data (already completed in a prior run)")

        # Stage 2: AnalyticsAgent
        if state["completed_stage"] == "data":
            self.log.info("running stage: analytics")
            state["analytics_output"] = self.analytics_agent.run(state["data_output"])
            state["completed_stage"] = "analytics"
            self._save_checkpoint(state)
        else:
            self.log.info("skipping stage: analytics (already completed in a prior run)")

        # Orchestrator-level decision, independent of any single agent
        kpis = state["analytics_output"]["kpis"]
        all_losing_money = all(kpi["roas"] < 1 for kpi in kpis.values())
        if all_losing_money:
            self.log.warning("ALERT: every channel is losing money -- escalating priority")

        # Stage 3: CopilotAgent
        if state["completed_stage"] == "analytics":
            self.log.info("running stage: copilot")
            state["copilot_output"] = self.copilot_agent.run(state["analytics_output"])
            state["completed_stage"] = "done"
            self._save_checkpoint(state)
        else:
            self.log.info("skipping stage: copilot (already completed in a prior run)")

        self.log.info("pipeline complete")

        report = state["copilot_output"]["report"]
        if all_losing_money:
            report = "*** URGENT REVIEW NEEDED ***\n\n" + report
        return report

    def reset(self) -> None:
        """Clears the checkpoint so the next run() starts from stage 1 again."""
        if os.path.exists(self.checkpoint_path):
            os.remove(self.checkpoint_path)
