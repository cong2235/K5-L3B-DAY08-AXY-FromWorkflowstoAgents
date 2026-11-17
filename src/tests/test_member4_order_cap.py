"""Vai 4 — trần hoàn tiền theo đơn trên shape nhóm chọn (workflow).

Bổ sung cho ma trận public T13/T14: kiểm thêm audit `policy_denied`, crash
giữa chừng trên claim chỉ được hoàn phần còn thiếu, và hai claim cùng một đơn.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lab8.db import connect
from lab8.durability import InjectedCrash, committed_audit_count
from lab8.policy import order_refunded_vnd
from lab8.shapes.workflow import run_claim

CRASH_POINTS = ["before_effect", "after_effect_before_checkpoint", "after_checkpoint"]


def _ledger(store: Path, claim_id: str) -> list[dict]:
    conn = connect(store)
    rows = [dict(r) for r in conn.execute("SELECT * FROM refund_ledger WHERE claim_id = ?", (claim_id,))]
    conn.close()
    return rows


def _order_total(store: Path, order_id: str) -> int:
    conn = connect(store)
    total = int(order_refunded_vnd(conn, order_id))
    conn.close()
    return total


def _audits(store: Path, claim_id: str, event_type: str) -> int:
    conn = connect(store)
    n = conn.execute(
        "SELECT COUNT(*) FROM audit_events WHERE claim_id = ? AND event_type = ?",
        (claim_id, event_type),
    ).fetchone()[0]
    conn.close()
    return int(n)


@pytest.mark.student
def test_fully_refunded_order_is_denied_with_policy_audit(public_db):
    """C-013: O-505 đã được hoàn trước đó. Quote đầy đủ, host từ chối."""
    result = run_claim("C-013", seed=11, store_path=str(public_db))
    assert result.status == "denied"
    assert result.proposal_amount == 35000
    assert result.refund_effects == []
    assert _ledger(public_db, "C-013") == []
    assert _audits(public_db, "C-013", "policy_denied") >= 1
    assert result.error_reason == "order_already_refunded"


@pytest.mark.student
def test_partial_prior_refund_tops_up_only_the_gap(public_db):
    """C-014: quote 150.000, đơn O-515 đã hoàn 30.000 → chỉ hoàn 120.000."""
    result = run_claim("C-014", seed=11, store_path=str(public_db))
    rows = _ledger(public_db, "C-014")
    assert result.status == "resolved"
    assert result.proposal_amount == 150000  # shape truyền quote đầy đủ
    assert len(rows) == 1
    assert int(rows[0]["amount_vnd"]) == 120000
    assert _order_total(public_db, "O-515") == 150000


@pytest.mark.student
@pytest.mark.parametrize("point", CRASH_POINTS)
def test_crash_on_top_up_claim_still_pays_the_gap_once(public_db, point):
    with pytest.raises(InjectedCrash):
        run_claim("C-014", seed=11, store_path=str(public_db), crash_at=point)
    resumed = run_claim("C-014", seed=22, store_path=str(public_db))
    again = run_claim("C-014", seed=33, store_path=str(public_db))

    rows = _ledger(public_db, "C-014")
    conn = connect(public_db)
    audits = committed_audit_count(conn, "C-014")
    conn.close()
    assert resumed.status == "resolved"
    assert again.status == "resolved"
    assert len(rows) == 1
    assert int(rows[0]["amount_vnd"]) == 120000
    assert audits == 1
    assert _order_total(public_db, "O-515") == 150000


@pytest.mark.student
def test_two_claims_on_one_order_never_exceed_the_cap(public_db):
    """C-001 và C-010 cùng đơn O-107: claim sau không được hoàn thêm."""
    first = run_claim("C-001", seed=11, store_path=str(public_db))
    second = run_claim("C-010", seed=11, store_path=str(public_db))
    assert first.status == "resolved"
    assert second.status == "denied"
    assert second.error_reason == "order_already_refunded"
    assert _ledger(public_db, "C-010") == []
    assert _order_total(public_db, "O-107") == 35000
