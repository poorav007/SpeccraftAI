"""Unit tests for `python -m speccraft.cli` extraction and `diff` subcommands."""

import json
from pathlib import Path

from speccraft.cli import run_cli

SAMPLES_DIR = Path(__file__).parent.parent / "samples"
EXPECTED_SPECS = SAMPLES_DIR / "expected_specs"
SHOP_APP_DIR = SAMPLES_DIR / "fastapi_shop_api"


def test_cli_diff_writes_cards_and_exits_1_on_breaking(tmp_path: Path):
    cards_out = tmp_path / "cards.json"
    summary_out = tmp_path / "diff_summary.md"

    code = run_cli(
        [
            "diff",
            str(EXPECTED_SPECS / "shop_v1.json"),
            str(EXPECTED_SPECS / "shop_v2.json"),
            "--cards-out",
            str(cards_out),
            "--summary-out",
            str(summary_out),
            "--fail-on-breaking",
        ]
    )
    assert code == 1
    assert cards_out.exists()
    assert summary_out.exists()

    cards_data = json.loads(cards_out.read_text(encoding="utf-8"))
    assert cards_data["summary"]["breaking_changes"] > 0
    assert len(cards_data["cards"]) > 0
    first_card = cards_data["cards"][0]
    assert set(["endpoint", "severity", "one_line_impact", "before", "after"]).issubset(
        first_card.keys()
    )

    md = summary_out.read_text(encoding="utf-8")
    assert "# SpecCraft AI — OpenAPI Diff Report" in md
    assert "BREAKING" in md


def test_cli_diff_exits_0_when_no_breaking_changes(tmp_path: Path):
    cards_out = tmp_path / "cards_same.json"
    code = run_cli(
        [
            "diff",
            str(EXPECTED_SPECS / "shop_v1.json"),
            str(EXPECTED_SPECS / "shop_v1.json"),
            "--cards-out",
            str(cards_out),
            "--fail-on-breaking",
        ]
    )
    assert code == 0
    cards_data = json.loads(cards_out.read_text(encoding="utf-8"))
    assert cards_data["summary"]["total_changes"] == 0
    assert cards_data["cards"] == []


def test_cli_diff_supports_static_ast_directory_comparison(tmp_path: Path):
    cards_out = tmp_path / "ast_cards.json"
    code = run_cli(
        [
            "diff",
            str(SHOP_APP_DIR),
            str(EXPECTED_SPECS / "shop_v2.json"),
            "--cards-out",
            str(cards_out),
        ]
    )
    assert code == 0
    assert cards_out.exists()


def test_cli_extract_backward_compatibility(capsys):
    code = run_cli([str(SHOP_APP_DIR), "--json"])
    assert code == 0
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert len(parsed["endpoints"]) > 0

