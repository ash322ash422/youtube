"""
agents/data_agent.py
----------------------
AGENT 1: DATA AGENT

Job: gather campaign performance data + industry benchmarks for the
AnalyticsAgent. This agent is the clearest example in the project of
genuine LLM-driven tool-calling: both tools take no arguments, so
there's no risk of the model needing to reproduce large data blobs in
its own output -- it just decides *whether and when* to call each one,
which is exactly the kind of decision tool-calling is good at.

DESIGN NOTE -- why the tools return small data, not raw dumps:
Real teams learn this the hard way: don't make the LLM a relay for
large payloads. Once a tool executes, its actual return value is
already sitting in your own Python process -- there's no need to ask
the model to copy it into its final answer. We capture each tool's
real output directly (see `self._captured`) and hand *that* forward to
the next agent. The model's final text is only ever used for the
human-readable status/plan, never as the source of truth for data.
"""

import csv

from agents.base_agent import BaseAgent
from agents.tool_schemas import EmptyInput
from logging_config import get_logger


class DataAgent(BaseAgent):

    SYSTEM_PROMPT = (
        "You are a data-gathering agent in a marketing analytics pipeline. "
        "Your job is to collect everything the next agent (which computes "
        "marketing KPIs) will need: raw campaign performance data and "
        "industry benchmark figures. Use the tools available to you to "
        "gather both. When you're done, briefly confirm what you gathered."
    )

    def __init__(self, csv_path: str, use_llm=None):
        super().__init__(name="DataAgent", use_llm=use_llm)
        self.csv_path = csv_path
        self._captured: dict = {}

        self.register_tool(
            name="read_internal_database",
            func=self._read_internal_database,
            description="Reads campaign performance rows (date, channel, impressions, clicks, spend, conversions, revenue) from the internal marketing database.",
            input_model=EmptyInput,
        )
        self.register_tool(
            name="fetch_external_benchmarks",
            func=self._fetch_external_benchmarks,
            description="Fetches current industry benchmark KPIs (CTR, CPA, ROAS) per marketing channel from an external analytics provider.",
            input_model=EmptyInput,
        )

    # ---- tool implementations ----
    def _read_internal_database(self) -> list[dict]:
        """
        Stands in for a real query, e.g. `SELECT * FROM campaign_daily
        WHERE date >= ...` against a warehouse. Swappable without
        touching anything else in this agent.
        """
        rows = []
        with open(self.csv_path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append({
                    "date": row["date"],
                    "channel": row["channel"],
                    "campaign": row["campaign"],
                    "impressions": int(row["impressions"]),
                    "clicks": int(row["clicks"]),
                    "spend": float(row["spend"]),
                    "conversions": int(row["conversions"]),
                    "revenue": float(row["revenue"]),
                })
        self._captured["campaign_data"] = rows
        return rows

    def _fetch_external_benchmarks(self) -> dict:
        """
        Stands in for a real external API call, e.g.
        `requests.get("https://api.adbenchmarks.com/v1/kpis").json()`.
        Hardcoded so this project needs no internet access or API key
        to demonstrate the pattern.
        """
        benchmarks = {
            "Google Search": {"ctr": 0.035, "cpa": 18.0, "roas": 2.0},
            "Facebook":      {"ctr": 0.020, "cpa": 22.0, "roas": 1.5},
            "Instagram":     {"ctr": 0.015, "cpa": 25.0, "roas": 1.2},
        }
        self._captured["benchmarks"] = benchmarks
        return benchmarks

    # ---- deterministic fallback path (no LLM/tool-calling) ----
    def _fallback_run(self) -> dict:
        log = get_logger(self.name)
        log.info("running in rule-based mode (no LLM) -- calling tools in fixed order")
        rows = self._read_internal_database()
        benchmarks = self._fetch_external_benchmarks()
        return {
            "campaign_data": rows,
            "benchmarks": benchmarks,
            "agent_summary": "[Rule-based mode] Loaded campaign data and benchmarks in fixed order.",
        }

    # ---- entry point ----
    def run(self) -> dict:
        self.log.info("starting run")

        if self._client is None:
            result = self._fallback_run()
        else:
            summary = self.run_agentic_loop(
                system_prompt=self.SYSTEM_PROMPT,
                user_message="Gather the campaign data and benchmarks needed for KPI analysis.",
            )
            result = {
                "campaign_data": self._captured.get("campaign_data", []),
                "benchmarks": self._captured.get("benchmarks", {}),
                "agent_summary": summary,
            }

        self.log.info("run complete", extra={
            "row_count": len(result["campaign_data"]),
            "channel_count": len(result["benchmarks"]),
        })
        return result
