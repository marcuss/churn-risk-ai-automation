"""HTTP endpoint wrapping the pipeline (Stretch A) — see docs/adr/0006.

  POST /churn-risk   body = CSV text → returns {flagged, delivered, message}
                     ?deliver=true also POSTs the briefing to the Slack webhook
  GET  /health       liveness check

Run:  pip install -e ".[api]"  then  python -m app.server  (or: flask --app app.server run)
"""

from __future__ import annotations

import io
import logging
from datetime import date

from flask import Flask, jsonify, request

from app.pipeline import summarize_flagged
from src.config import Config
from src.ingestion.csv_loader import load_accounts
from src.messaging import slack_client, slack_formatter

logger = logging.getLogger(__name__)
app = Flask(__name__)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/churn-risk")
def churn_risk():
    raw = request.get_data(as_text=True)
    if not raw.strip():
        return jsonify({"error": "empty request body; expected CSV"}), 400

    try:
        accounts = load_accounts(io.StringIO(raw))
    except ValueError as exc:  # missing required columns / unreadable CSV
        return jsonify({"error": str(exc)}), 400

    # Optional ?today=YYYY-MM-DD override so a fixed dataset yields reproducible output.
    today_param = request.args.get("today")
    try:
        today = date.fromisoformat(today_param) if today_param else date.today()
    except ValueError:
        return jsonify({"error": f"invalid 'today' date: {today_param!r}"}), 400

    config = Config.from_env()
    summarized = summarize_flagged(accounts, config, today)
    payload = slack_formatter.build_payload(summarized)

    delivered = False
    if request.args.get("deliver") == "true" and config.slack_webhook_url:
        slack_client.send(config.slack_webhook_url, payload)
        delivered = True

    return jsonify({"flagged": len(summarized), "delivered": delivered, "message": payload})


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    app.run(host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
