"""Tests for GitHub Repo URL parsing/SSRF guards and Mobile -> GitHub PR comment bridge."""

from fastapi.testclient import TestClient

from speccraft.api.routes import format_pr_review_markdown, parse_github_repo_url
from speccraft.api.server import app


def test_parse_github_repo_url_valid_and_ssrf_rejected():
    owner, repo, ref = parse_github_repo_url("https://github.com/poorav007/SpeccraftAI")
    assert (owner, repo, ref) == ("poorav007", "SpeccraftAI", None)

    o2, r2, ref2 = parse_github_repo_url("https://github.com/tiangolo/fastapi/tree/master")
    assert (o2, r2, ref2) == ("tiangolo", "fastapi", "master")

    for bad_url in (
        "http://github.com/owner/repo",
        "https://evil.internal/owner/repo",
        "http://169.254.169.254/latest/meta-data",
        "https://github.com/only-owner",
    ):
        try:
            parse_github_repo_url(bad_url)
            raise AssertionError(f"Expected ValueError for {bad_url}")
        except ValueError:
            pass


def test_parse_github_rejects_bad_url_over_api():
    client = TestClient(app)
    res = client.post("/api/parse/github", json={"repo_url": "http://127.0.0.1:8000/secret"})
    assert res.status_code == 400


def test_format_and_post_github_pr_review_without_token_returns_preview(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    decisions = [
        {
            "endpoint": "POST /orders",
            "severity": "breaking",
            "decision": "blocked",
            "one_line_impact": "Added required billing_zip field.",
        },
        {
            "endpoint": "GET /items",
            "severity": "non_breaking",
            "decision": "approved",
            "one_line_impact": "Added optional filter query param.",
        },
    ]

    md = format_pr_review_markdown(decisions, "Reviewed via SpecCraft Mobile")
    assert "API Review Blocked" in md
    assert "**Approved**: `1` | **Blocked**: `1`" in md
    assert "🚨 BLOCKED" in md
    assert "✅ APPROVED" in md

    client = TestClient(app)
    res = client.post(
        "/api/github/pr-review",
        json={
            "owner": "poorav007",
            "repo": "SpeccraftAI",
            "pr_number": 12,
            "decisions": decisions,
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["posted"] is False
    assert "POST /orders" in body["comment_markdown"]

