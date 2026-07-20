"""
tests/test_analytics_agent.py
--------------------------------
INDUSTRY PATTERN: test the deterministic parts, always.

You cannot unit-test "did the LLM say something reasonable" in the
usual sense (that's what evals/LLM-as-judge frameworks are for). But
every deterministic function in this project -- the math, the rule
engine -- absolutely should have ordinary unit tests, and they should
run in CI on every commit with zero network access or API key needed.

Run with:
    pytest tests/
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.analytics_agent import AnalyticsAgent
from agents.copilot_agent import CopilotAgent


def make_agent():
    # use_llm=False -> no Anthropic client is created, no API key needed
    return AnalyticsAgent(use_llm=False)


def test_compute_kpis_basic_math():
    agent = make_agent()
    rows = [
        {"channel": "Google Search", "impressions": 1000, "clicks": 100,
         "spend": 200.0, "conversions": 10, "revenue": 500.0},
        {"channel": "Google Search", "impressions": 1000, "clicks": 100,
         "spend": 200.0, "conversions": 10, "revenue": 500.0},
    ]
    benchmarks = {"Google Search": {"ctr": 0.05, "cpa": 20.0, "roas": 2.0}}

    kpis = agent.compute_kpis(rows, benchmarks)

    assert "Google Search" in kpis
    result = kpis["Google Search"]
    assert result["ctr"] == 0.1          # 200 clicks / 2000 impressions
    assert result["cpc"] == 2.0          # 400 spend / 200 clicks
    assert result["cpa"] == 20.0         # 400 spend / 20 conversions
    assert result["roas"] == 2.5         # 1000 revenue / 400 spend


def test_compute_kpis_handles_zero_impressions_without_crashing():
    agent = make_agent()
    rows = [{"channel": "Facebook", "impressions": 0, "clicks": 0,
              "spend": 0.0, "conversions": 0, "revenue": 0.0}]
    kpis = agent.compute_kpis(rows, benchmarks={})
    assert kpis["Facebook"]["ctr"] == 0
    assert kpis["Facebook"]["roas"] == 0


def test_rule_based_decision_reduce_when_losing_money():
    agent = CopilotAgent(use_llm=False)
    kpis = {"Instagram": {"roas": 0.8, "benchmark_roas": 1.2}}
    decisions = agent._rule_based_decision(kpis)
    assert decisions["Instagram"] == "REDUCE"


def test_rule_based_decision_increase_when_far_above_benchmark():
    agent = CopilotAgent(use_llm=False)
    kpis = {"Google Search": {"roas": 3.0, "benchmark_roas": 2.0}}
    decisions = agent._rule_based_decision(kpis)
    assert decisions["Google Search"] == "INCREASE"


def test_apply_recommendation_auto_approves_when_configured(monkeypatch):
    import config as cfg
    monkeypatch.setattr(cfg, "AUTO_APPROVE_ACTIONS", True)
    agent = CopilotAgent(use_llm=False)
    result = agent._apply_recommendation(channel="Facebook", action="MONITOR", rationale="test")
    assert result["status"] == "approved"
