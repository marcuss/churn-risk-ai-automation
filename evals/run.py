"""Eval harness — executes evals/rubric.md against evals/golden_set.jsonl.

For each golden account it generates the summary with the production `LLMClient`,
runs deterministic output checks (Layer 1), scores quality with an LLM-as-judge at
temperature 0 (Layer 2), aggregates, and — with `--check` — exits non-zero when the
suite is below the quality bar (the gate run by `evals.yml`). The rubric is the
source of truth; this file executes it.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from statistics import mean

from src.ai.llm_client import LLMClient
from src.config import Config
from src.models import Account, RiskAssessment, SubscriptionStatus
from src.risk.risk_scoring import assess

EVAL_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = EVAL_DIR.parent / "prompts"
GOLDEN_SET = EVAL_DIR / "golden_set.jsonl"
REPORT_FILE = EVAL_DIR / "report.md"

REFERENCE_DATE = date(2026, 6, 11)
JUDGE_DIMENSIONS = ("synthesis", "tone", "actionability", "faithfulness", "canceled_framing")

CASE_JUDGE_BAR = 4.0     # per-case mean judge score
SUITE_JUDGE_BAR = 4.0    # suite-wide mean judge score
SUITE_LAYER1_BAR = 0.9   # fraction of cases that must pass every Layer-1 check


# --------------------------------------------------------------------------- #
# Layer 1 — deterministic checks (pure; unit-tested without the API)
# --------------------------------------------------------------------------- #


def layer1_checks(summary: str, account_name: str, status: SubscriptionStatus) -> dict[str, bool]:
    text = summary.strip()
    checks = {
        "non_empty": bool(text),
        "length_ok": 20 <= len(text) <= 800,
        "max_4_sentences": len(re.findall(r"[.!?]+", text)) <= 4,
        "no_bullets_or_headings": re.search(r"(?m)^\s*([-*•]|\d+\.|#)", text) is None,
        "omits_account_name": account_name.casefold() not in text.casefold(),
        "no_leaked_score": "score" not in text.casefold(),
    }
    if status is SubscriptionStatus.CANCELED:
        checks["canceled_mentions_renewal"] = (
            re.search(r"renew|non-renewal|cancel|save", text, re.I) is not None
        )
    return checks


# --------------------------------------------------------------------------- #
# Layer 2 — LLM-as-judge
# --------------------------------------------------------------------------- #


@dataclass
class JudgeResult:
    scores: dict[str, int]
    rationale: str

    @property
    def mean(self) -> float:
        return mean(self.scores.values()) if self.scores else 0.0


def parse_judge_scores(raw: str) -> JudgeResult:
    match = re.search(r"\{.*\}", raw, re.S)
    data = json.loads(match.group(0)) if match else {}
    scores = {dim: int(data.get(dim, 0)) for dim in JUDGE_DIMENSIONS}
    return JudgeResult(scores=scores, rationale=str(data.get("rationale", "")))


def judge_summary(client, model: str, summary: str, context: str, signals: str) -> JudgeResult:
    prompt = (PROMPTS_DIR / "eval_judge_prompt.txt").read_text(encoding="utf-8").format(
        account_block=context, signals=signals, summary=summary
    )
    message = client.messages.create(
        model=model,
        max_tokens=300,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = "".join(b.text for b in message.content if getattr(b, "type", None) == "text")
    return parse_judge_scores(raw)


# --------------------------------------------------------------------------- #
# Case result + aggregation
# --------------------------------------------------------------------------- #


@dataclass
class CaseResult:
    name: str
    score: int
    layer1: dict[str, bool]
    judge: JudgeResult
    summary: str

    @property
    def layer1_pass(self) -> bool:
        return all(self.layer1.values())

    @property
    def passed(self) -> bool:
        return self.layer1_pass and self.judge.mean >= CASE_JUDGE_BAR


def suite_passes(cases: list[CaseResult]) -> bool:
    if not cases:
        return False
    layer1_rate = mean(1.0 if c.layer1_pass else 0.0 for c in cases)
    judge_avg = mean(c.judge.mean for c in cases)
    return layer1_rate >= SUITE_LAYER1_BAR and judge_avg >= SUITE_JUDGE_BAR


# --------------------------------------------------------------------------- #
# Run
# --------------------------------------------------------------------------- #


def _context_block(account: Account) -> str:
    return (
        f"Subscription Status: {account.subscription_status.value}\n"
        f"Failed Payments (30d): {account.failed_payment_count_last_30d}\n"
        f"Days Since Last Login: {account.days_since_last_login}\n"
        f"Open Support Tickets: {account.open_support_tickets}\n"
        f"Renewal in days: {account.days_until_renewal(REFERENCE_DATE)}"
    )


def run_eval(config: Config) -> list[CaseResult]:
    from anthropic import Anthropic

    client = Anthropic(api_key=config.anthropic_api_key)
    llm = LLMClient(config, client=client)
    cases: list[CaseResult] = []
    for line in GOLDEN_SET.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        expected = record.pop("expected", {})
        account = Account.from_csv_row({k: str(v) for k, v in record.items()})
        assessment: RiskAssessment = assess(account, REFERENCE_DATE)
        exp_flag = expected.get("is_flagged")
        if exp_flag is not None and assessment.is_flagged != exp_flag:
            print(f"  WARN: {account.account_name} flag != golden", file=sys.stderr)

        try:
            summary = llm.generate_summary(assessment, REFERENCE_DATE)
        except Exception as exc:  # noqa: BLE001 — a failed generation is just a failed case
            summary = ""
            print(f"  generation failed for {account.account_name}: {exc}", file=sys.stderr)

        if summary:
            judged = judge_summary(
                client, config.model, summary, _context_block(account),
                ", ".join(assessment.signals),
            )
        else:
            judged = JudgeResult(scores=dict.fromkeys(JUDGE_DIMENSIONS, 0), rationale="no summary")

        cases.append(
            CaseResult(
                name=account.account_name,
                score=assessment.score,
                layer1=layer1_checks(summary, account.account_name, account.subscription_status),
                judge=judged,
                summary=summary,
            )
        )
    return cases


def render_report(cases: list[CaseResult]) -> str:
    lines = ["# Eval Report", ""]
    for c in cases:
        verdict = "PASS" if c.passed else "FAIL"
        failed = [k for k, v in c.layer1.items() if not v]
        l1 = "all pass" if not failed else "FAILED: " + ", ".join(failed)
        dims = " ".join(f"{d}={c.judge.scores[d]}" for d in JUDGE_DIMENSIONS)
        lines += [
            f"## {c.name} (score {c.score}) — {verdict}",
            f"- Layer 1: {l1}",
            f"- Judge ({c.judge.mean:.1f}): {dims}",
            f"- _{c.judge.rationale}_",
            "",
        ]
    layer1_rate = mean(1.0 if c.layer1_pass else 0.0 for c in cases) if cases else 0.0
    judge_avg = mean(c.judge.mean for c in cases) if cases else 0.0
    lines += [
        "## Suite",
        f"- Layer-1 pass rate: {layer1_rate:.0%} (bar {SUITE_LAYER1_BAR:.0%})",
        f"- Mean judge score: {judge_avg:.2f} (bar {SUITE_JUDGE_BAR:.1f})",
        f"- **{'PASS' if suite_passes(cases) else 'FAIL'}**",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the churn-summary quality eval.")
    parser.add_argument("--check", action="store_true", help="exit non-zero if below the bar")
    args = parser.parse_args(argv)

    config = Config.from_env()
    if not config.anthropic_api_key:
        print("ANTHROPIC_API_KEY required to run evals", file=sys.stderr)
        sys.exit(2)

    cases = run_eval(config)
    report = render_report(cases)
    print(report)
    REPORT_FILE.write_text(report + "\n", encoding="utf-8")

    if args.check and not suite_passes(cases):
        sys.exit(1)


if __name__ == "__main__":
    main()
