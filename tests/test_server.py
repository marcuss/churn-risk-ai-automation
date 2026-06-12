"""Tests for the HTTP endpoint (Stretch A).

Run offline: the config is patched to have no API key, so summaries take the
deterministic-fallback path (no network) and nothing is delivered.
"""

import pytest

pytest.importorskip("flask")  # the endpoint is an optional extra

from app import server  # noqa: E402
from src.config import Config  # noqa: E402

SAMPLE_CSV = (
    "account_id,account_name,mrr,plan_name,subscription_status,"
    "failed_payment_count_last_30d,days_since_last_login,open_support_tickets,contract_end_date\n"
    "acct_1,Acme Corp,5000,Growth,past_due,2,40,4,2026-12-01\n"
    "acct_2,Healthy Co,3000,Growth,active,0,3,0,2027-01-01\n"
)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(
        Config,
        "from_env",
        classmethod(
            lambda cls: Config(
                anthropic_api_key=None, slack_webhook_url=None, slack_alert_webhook_url=None
            )
        ),
    )
    return server.app.test_client()


def test_health_ok(client):
    assert client.get("/health").get_json() == {"status": "ok"}


def test_churn_risk_returns_formatted_briefing(client):
    resp = client.post("/churn-risk", data=SAMPLE_CSV, content_type="text/csv")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["flagged"] == 1  # Acme flagged, Healthy Co not
    assert body["delivered"] is False
    assert "Acme Corp" in body["message"]["text"]
    assert body["message"]["blocks"]  # Block Kit present


def test_empty_body_is_400(client):
    resp = client.post("/churn-risk", data="", content_type="text/csv")
    assert resp.status_code == 400


def test_malformed_csv_is_400(client):
    resp = client.post("/churn-risk", data="not,a,valid,header\n1,2,3,4", content_type="text/csv")
    assert resp.status_code == 400


BORDERLINE_CSV = (
    "account_id,account_name,mrr,plan_name,subscription_status,"
    "failed_payment_count_last_30d,days_since_last_login,open_support_tickets,contract_end_date\n"
    "acct_b,Borderline Co,2000,Growth,active,1,40,0,2026-12-25\n"
)


def test_today_override_changes_renewal_proximity(client):
    # Borderline Co sits at 5 points (1 failed payment + 40 idle days). Far from
    # renewal it stays unflagged; pin today within the renewal window and the
    # proximity points tip it over the threshold.
    far = client.post("/churn-risk?today=2026-06-11", data=BORDERLINE_CSV, content_type="text/csv")
    near = client.post("/churn-risk?today=2026-12-20", data=BORDERLINE_CSV, content_type="text/csv")
    assert far.get_json()["flagged"] == 0
    assert near.get_json()["flagged"] == 1


def test_invalid_today_is_400(client):
    resp = client.post("/churn-risk?today=not-a-date", data=SAMPLE_CSV, content_type="text/csv")
    assert resp.status_code == 400
