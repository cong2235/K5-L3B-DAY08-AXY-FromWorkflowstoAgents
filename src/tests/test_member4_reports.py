"""Vai 4 — evaluation: report đã commit phải nhất quán với nhau và với ADR.

Chỉ đọc file, không chạy lại benchmark hay ghi gì vào `reports/`.
"""

from __future__ import annotations

import json
import re

import pytest

from lab8.config_loader import repo_path

SEEDS = [11, 22, 33, 44, 55]
SHAPES = {"workflow", "single", "orchestrator", "swarm"}
FORBIDDEN = ("CANARY_SECRET_", "parent_secret", "raw_headers")


def _load(name: str) -> dict:
    return json.loads(repo_path("reports", name).read_text(encoding="utf-8"))


def _adr() -> str:
    return (repo_path().parent / "report" / "team" / "decision_adr.md").read_text(encoding="utf-8")


@pytest.mark.student
def test_benchmark_covers_four_shapes_five_seeds_ten_claims():
    bench = _load("benchmark.json")
    controlled = bench["controlled_variables"]
    assert controlled["seeds"] == SEEDS
    assert len(controlled["claim_ids"]) >= 10
    assert set(bench["by_shape"]) == SHAPES
    n_claims = len(controlled["claim_ids"])
    for shape, row in bench["by_shape"].items():
        assert row["trials"] == n_claims * len(SEEDS), shape
        trials = [t for t in bench["trials"] if t["shape"] == shape]
        assert len(trials) == row["trials"], shape
        assert row["successes"] == sum(1 for t in trials if t["passed"]), shape


@pytest.mark.student
def test_crash_report_is_twenty_of_twenty():
    crash = _load("crash.json")
    assert crash["count"] == 20
    assert crash["passed"] == 20
    assert crash["crash_safety"] == "20/20"


@pytest.mark.student
def test_hidden_selfcheck_runs_clean_for_every_shape():
    hidden = _load("hidden_selfcheck.json")
    seeds = hidden["controlled_variables"]["seeds"]
    n_claims = len(hidden["controlled_variables"]["claim_ids"])
    assert seeds == SEEDS
    assert n_claims == 40
    for shape, row in hidden["by_shape"].items():
        assert row["trials"] == n_claims * len(seeds), shape
    statuses = {t["status"] for t in hidden["trials"]}
    assert statuses <= {"resolved", "denied", "escalated", "needs_info", "failed"}
    assert not any(t["reason"] == "leak_suspect" for t in hidden["trials"])
    blob = json.dumps(hidden, ensure_ascii=False)
    for needle in FORBIDDEN:
        assert needle not in blob


@pytest.mark.student
def test_adr_matches_benchmark_for_the_chosen_shape():
    adr = _adr()
    bench = _load("benchmark.json")
    chosen = re.search(r"^- Shape chọn:\s*(\w+)", adr, re.M).group(1)
    assert chosen in bench["by_shape"]
    row = bench["by_shape"][chosen]

    run_id = re.search(r"`(R-[\w-]+)`", adr.split("- Run id dẫn chứng:")[1]).group(1)
    assert any(t["run_id"] == run_id and t["shape"] == chosen for t in bench["trials"])

    cost_line = re.search(r"^- Cost per success[^:]*:\s*([\d.,]+)", adr, re.M).group(1)
    cost = float(cost_line.rstrip(".").replace(",", "."))
    assert cost == pytest.approx(row["cost_per_success_vnd"], abs=0.01)

    if row["pass_rate"] == 1.0:
        assert "100%" in adr.split("- Pass rate")[1].splitlines()[0]
    assert "20/20" in adr
