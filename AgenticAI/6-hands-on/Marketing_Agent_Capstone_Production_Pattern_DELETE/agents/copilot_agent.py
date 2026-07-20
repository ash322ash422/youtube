"""
agents/copilot_agent.py
--------------------------
AGENT 3: COPILOT AGENT (decision support)

Job: turn KPIs + analyst notes into channel-level budget recommendations,
and a short executive summary a manager could read in 30 seconds.

DESIGN NOTE -- deterministic decision, LLM-written rationale:
The actual INCREASE/MAINTAIN/MONITOR/REDUCE decision is computed by
`_rule_based_decision`, plain if/else logic against ROAS vs. benchmark.
This is deliberate: a budget decision needs to be consistent and
auditable ("why did the system say REDUCE?" should always have the same,
inspectable answer), so it isn't something we hand to a non-deterministic
model. The LLM's job is to explain the decision in plain language and
decide whether historical context (via `get_past_recommendations`)
would sharpen that explanation -- reasoning and communication, not the
underlying arithmetic.

DESIGN NOTE -- human-in-the-loop for the one WRITE tool:
`apply_recommendation` is the only tool in this project that changes
state rather than just reading it (it stands in for something like
"push this budget change to the ads platform"). Any tool call that
would send, modify, or delete something on a person's behalf should
require an explicit approval step before it executes -- see
`_request_human_approval`. This applies regardless of whether the
model or the deterministic rule engine decided on the action; the LLM
deciding something is not authorization to act on it.
"""

import os

import config
from agents.base_agent import BaseAgent
from agents.tool_schemas import GetPastRecommendationsInput, ApplyRecommendationInput
from logging_config import get_logger


class CopilotAgent(BaseAgent):

    SYSTEM_PROMPT = (
        "You are a marketing decision-support copilot. You will be given KPIs, "
        "analyst notes, and a REQUIRED action per channel that has already been "
        "decided by a deterministic rules engine (do not change these actions). "
        "Your job: for EACH channel, call apply_recommendation exactly once with "
        "that channel's required action and a one-to-two sentence rationale "
        "grounded in the KPIs and notes you were given. You may call "
        "get_past_recommendations first if recent history would sharpen your "
        "rationale (e.g. to note that a decision changed from last time). "
        "After all channels are submitted, write a 3-5 sentence executive summary."
    )

    def __init__(self, use_llm=None):
        super().__init__(name="CopilotAgent", use_llm=use_llm)
        self._applied: dict = {}

        self.register_tool(
            name="get_past_recommendations",
            func=self._get_past_recommendations,
            description="Retrieves this agent's most recent past recommendations from memory, useful for noting changes over time.",
            input_model=GetPastRecommendationsInput,
        )
        self.register_tool(
            name="apply_recommendation",
            func=self._apply_recommendation,
            description="Submits a budget recommendation for one channel. This is a WRITE action and requires human approval before it takes effect.",
            input_model=ApplyRecommendationInput,
        )

    # ---- deterministic decision engine (never delegated to the LLM) ----
    def _rule_based_decision(self, kpis: dict) -> dict:
        decisions = {}
        for channel, kpi in kpis.items():
            bench_roas = kpi.get("benchmark_roas") or 1.0
            if kpi["roas"] < 1:
                decisions[channel] = "REDUCE"
            elif kpi["roas"] >= bench_roas * 1.2:
                decisions[channel] = "INCREASE"
            elif kpi["roas"] < bench_roas * 0.8:
                decisions[channel] = "MONITOR"
            else:
                decisions[channel] = "MAINTAIN"
        return decisions

    # ---- tool: read-only, safe to let the LLM call freely ----
    def _get_past_recommendations(self, limit: int) -> list[dict]:
        return self.recall(n=limit, event_type="recommendation_applied")

    # ---- tool: WRITE action, gated behind human approval ----
    def _apply_recommendation(self, channel: str, action: str, rationale: str) -> dict:
        if config.AUTO_APPROVE_ACTIONS:
            approved = True
            self.log.info("auto-approved (AUTO_APPROVE_ACTIONS=true)", extra={"channel": channel})
        else:
            approved = self._request_human_approval(channel, action, rationale)

        status = "approved" if approved else "rejected_by_human_reviewer"
        record = {"channel": channel, "action": action, "rationale": rationale,
                   "approved": approved, "status": status}
        self._applied[channel] = record

        event_type = "recommendation_applied" if approved else "recommendation_rejected"
        self.remember({"type": event_type, **record})
        return record

    def _request_human_approval(self, channel: str, action: str, rationale: str) -> bool:
        """
        A real production system would route this through a proper
        approval UI, Slack message, or ticketing workflow, and probably
        let a request wait asynchronously for a reviewer. A blocking
        `input()` prompt is the simplest possible stand-in for that same
        idea: nothing gets applied until a human explicitly says yes.
        """
        print(f"\n[HUMAN APPROVAL REQUIRED] {channel}: recommended action = {action}")
        print(f"  Rationale: {rationale}")
        try:
            answer = input("  Approve this action? [y/N]: ").strip().lower()
        except EOFError:
            self.log.warning("no interactive input available; defaulting to NOT approved",
                              extra={"channel": channel})
            return False
        return answer == "y"

    # ---- deterministic fallback path (no LLM/tool-calling) ----
    def _fallback_run(self, decisions: dict) -> str:
        log = get_logger(self.name)
        log.info("running in rule-based mode (no LLM)")
        for channel, action in decisions.items():
            self._apply_recommendation(
                channel=channel, action=action,
                rationale=f"[Rule-based mode] ROAS-vs-benchmark rule selected {action}.",
            )
        return "[Rule-based mode] Recommendations were generated by the rules engine with templated rationale (no LLM configured)."

    # ---- entry point ----
    def run(self, analytics_output: dict) -> dict:
        self.log.info("starting run")
        kpis = analytics_output["kpis"]
        notes = analytics_output["notes"]

        decisions = self._rule_based_decision(kpis)
        self.log.info("computed required actions", extra={"decisions": decisions})

        if self._client is None:
            summary = self._fallback_run(decisions)
        else:
            user_message = (
                f"KPIs: {kpis}\n\n"
                f"Analyst notes: {notes}\n\n"
                f"Required actions (already decided, do not change): {decisions}\n\n"
                "Submit each channel's required action via apply_recommendation, "
                "then write your executive summary."
            )
            summary = self.run_agentic_loop(system_prompt=self.SYSTEM_PROMPT, user_message=user_message)

        applied = self._applied  # ground truth of what actually got approved/rejected
        header = "MARKETING CAMPAIGN ANALYSIS - DECISION SUPPORT REPORT\n" + "=" * 55
        lines = []
        for channel, action in decisions.items():
            record = applied.get(channel, {})
            status = record.get("status", "not submitted")
            lines.append(f"- {channel}: {action}  [{status}]")
        decisions_block = "\n".join(lines)

        report = f"{header}\n\n{summary}\n\nDecisions by channel:\n{decisions_block}\n"
        return {"report": report, "decisions": decisions, "applied": applied}
