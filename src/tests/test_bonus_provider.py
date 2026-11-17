"""B5: external effects, local ledger, crash windows and recovery boundaries."""

import json
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path

import pytest

from bonus.provider import Provider, ProviderConflict
from bonus.provider_workflow import POINTS, pay_refund, reconcile, run_with_provider
from lab8.db import connect
from lab8.durability import InjectedCrash, committed_audit_count, get_refund, issue_refund
from lab8.metrics import trial_pass
from tests.conftest import BY_ID


@pytest.fixture(autouse=True)
def isolated_traces(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


def pay(store, provider, claim_id="C-001", proposal=35000, **kwargs):
    with closing(connect(store)) as conn:
        return pay_refund(conn, claim_id, proposal, provider, **kwargs)


def recover(store, provider):
    with closing(connect(store)) as conn:
        return reconcile(conn, provider)


def check_effects(store, provider, claim_id, amount):
    receipts = provider.lookup(f"refund:{claim_id}")
    assert len(receipts) == 1
    assert receipts[0]["amount_vnd"] == amount
    with closing(connect(store)) as conn:
        assert get_refund(conn, claim_id)["amount_vnd"] == amount
        assert committed_audit_count(conn, claim_id) == 1
        assert conn.execute("SELECT COUNT(*) FROM bonus_provider_audit WHERE claim_id = ?", (claim_id,)).fetchone()[0] == 1


def test_provider_replays_one_effect_across_restart(tmp_path):
    path = tmp_path / "provider.sqlite"
    first = Provider(path).refund("refund:C-001", 35000)
    restarted = Provider(path)
    assert restarted.refund("refund:C-001", 35000) == first
    assert len(restarted.lookup("refund:C-001")) == 1


def test_provider_rejects_changed_amount(tmp_path):
    provider = Provider(tmp_path / "provider.sqlite")
    provider.refund("refund:C-001", 35000)
    with pytest.raises(ProviderConflict):
        provider.refund("refund:C-001", 10000)
    assert [r["amount_vnd"] for r in provider.lookup("refund:C-001")] == [35000]


@pytest.mark.parametrize("amount", [0, -1])
def test_provider_rejects_nonpositive_amount(tmp_path, amount):
    provider = Provider(tmp_path / "provider.sqlite")
    with pytest.raises(ValueError):
        provider.refund("refund:C-001", amount)
    assert provider.lookup("refund:C-001") == []


@pytest.mark.parametrize("recovery", ["retry", "reconcile"])
@pytest.mark.parametrize("point", POINTS)
@pytest.mark.parametrize("claim_id,proposal,amount", [
    ("C-001", 35000, 35000),
    ("C-003", 150000, 150000),
    ("C-008", 35000, 20000),
    ("C-014", 150000, 120000),
])
def test_crash_recovery_keeps_one_external_and_local_effect(public_db, tmp_path, recovery, point, claim_id, proposal, amount):
    path = tmp_path / "provider.sqlite"
    provider = Provider(path)
    with pytest.raises(InjectedCrash, match=point):
        pay(public_db, provider, claim_id, proposal, crash_at=point)
    with closing(connect(public_db)) as conn:
        committed = point == "after_confirm_before_audit"
        assert (get_refund(conn, claim_id) is not None) == committed
        assert committed_audit_count(conn, claim_id) == int(committed)
        assert conn.execute("SELECT COUNT(*) FROM bonus_provider_audit").fetchone()[0] == 0
    assert len(provider.lookup(f"refund:{claim_id}")) == int(point != "after_reserve_before_provider")
    provider = Provider(path)
    if recovery == "retry":
        assert pay(public_db, provider, claim_id, proposal)["ok"]
    else:
        outcomes = recover(public_db, provider)
        assert len(outcomes) == 1 and outcomes[0]["ok"]
    assert pay(public_db, provider, claim_id, proposal)["ok"]
    assert recover(public_db, provider) == []
    check_effects(public_db, provider, claim_id, amount)


def test_no_dedupe_blind_retry_duplicates_payment_but_not_ledger(public_db, tmp_path):
    provider = Provider(tmp_path / "provider.sqlite", dedupe=False)
    with pytest.raises(InjectedCrash):
        pay(public_db, provider, crash_at="after_provider_before_confirm")
    assert pay(public_db, provider)["ok"]
    assert len(provider.lookup("refund:C-001")) == 2
    with closing(connect(public_db)) as conn:
        assert get_refund(conn, "C-001")["amount_vnd"] == 35000
        assert committed_audit_count(conn, "C-001") == 1


@pytest.mark.parametrize("point", POINTS)
def test_reconciliation_can_reuse_a_visible_receipt_without_dedupe(public_db, tmp_path, point):
    provider = Provider(tmp_path / "provider.sqlite", dedupe=False)
    with pytest.raises(InjectedCrash):
        pay(public_db, provider, crash_at=point)
    assert recover(public_db, provider)[0]["ok"]
    check_effects(public_db, provider, "C-001", 35000)


@pytest.mark.parametrize("change,reason", [
    ("missing", "missing_approval"),
    ("expired", "approval_expired"),
    ("revoked", "approval_revoked"),
    ("other_claim", "approval_claim_mismatch"),
    ("zero", "non_positive_amount"),
])
def test_invalid_approval_never_reaches_provider(public_db, tmp_path, change, reason):
    provider = Provider(tmp_path / "provider.sqlite")
    changes = {
        "missing": "UPDATE claims SET approval_id = NULL WHERE claim_id = 'C-001'",
        "expired": "UPDATE approvals SET expires_at = '2020-01-01' WHERE approval_id = 'A-001'",
        "revoked": "UPDATE approvals SET status = 'revoked' WHERE approval_id = 'A-001'",
        "other_claim": "UPDATE approvals SET claim_id = 'C-OTHER' WHERE approval_id = 'A-001'",
        "zero": "UPDATE approvals SET approved_vnd = 0 WHERE approval_id = 'A-001'",
    }
    with closing(connect(public_db)) as conn:
        conn.execute(changes[change])
        conn.commit()
        result = pay_refund(conn, "C-001", 35000, provider)
        assert not result["ok"] and result["reason"] == reason
        assert get_refund(conn, "C-001") is None
        assert conn.execute("SELECT COUNT(*) FROM audit_events WHERE event_type = 'policy_denied'").fetchone()[0] == 1
    assert provider.lookup("refund:C-001") == []


def test_pending_order_blocks_a_second_claim_until_reconciled(public_db, tmp_path):
    provider = Provider(tmp_path / "provider.sqlite")
    with pytest.raises(InjectedCrash):
        pay(public_db, provider, crash_at=POINTS[0])
    blocked = pay(public_db, provider, "C-010", 35000)
    assert not blocked["ok"] and blocked["reason"] == "order_pending"
    assert provider.lookup("refund:C-010") == []
    assert recover(public_db, provider)[0]["ok"]
    assert pay(public_db, provider, "C-010", 35000)["reason"] == "order_already_refunded"


def test_changed_proposal_cannot_alter_reserved_payment(public_db, tmp_path):
    provider = Provider(tmp_path / "provider.sqlite")
    with pytest.raises(InjectedCrash):
        pay(public_db, provider, crash_at=POINTS[0])
    assert pay(public_db, provider, proposal=10000)["reason"] == "amount_conflict"
    assert provider.lookup("refund:C-001") == []


def test_existing_unmanaged_ledger_does_not_trigger_external_payment(public_db, tmp_path):
    with closing(connect(public_db)) as conn:
        issue_refund(conn, "C-001", 35000)
    provider = Provider(tmp_path / "provider.sqlite")
    assert pay(public_db, provider)["reason"] == "unmanaged_refund"
    assert provider.lookup("refund:C-001") == []


def test_revoked_approval_after_payment_holds_recovery_without_resending(public_db, tmp_path):
    provider = Provider(tmp_path / "provider.sqlite")
    with pytest.raises(InjectedCrash):
        pay(public_db, provider, crash_at=POINTS[1])
    with closing(connect(public_db)) as conn, conn:
        conn.execute("UPDATE approvals SET status = 'revoked' WHERE approval_id = 'A-001'")
    assert recover(public_db, provider)[0]["reason"] == "approval_revoked"
    assert len(provider.lookup("refund:C-001")) == 1
    with closing(connect(public_db)) as conn, conn:
        assert get_refund(conn, "C-001") is None
        conn.execute("UPDATE approvals SET status = 'valid' WHERE approval_id = 'A-001'")
    assert recover(public_db, provider)[0]["ok"]
    check_effects(public_db, provider, "C-001", 35000)


def test_ambiguous_provider_history_requires_review(public_db, tmp_path):
    provider = Provider(tmp_path / "provider.sqlite", dedupe=False)
    with pytest.raises(InjectedCrash):
        pay(public_db, provider, crash_at=POINTS[1])
    provider.refund("refund:C-001", 35000)
    result = recover(public_db, provider)[0]
    assert not result["ok"] and result["reason"] == "provider_ambiguous"
    with closing(connect(public_db)) as conn:
        assert get_refund(conn, "C-001") is None


def test_mismatched_receipt_cannot_confirm_a_reservation(public_db, tmp_path):
    provider = Provider(tmp_path / "provider.sqlite")
    with pytest.raises(InjectedCrash):
        pay(public_db, provider, crash_at=POINTS[0])
    provider.refund("refund:C-001", 1)
    assert recover(public_db, provider)[0]["reason"] == "provider_amount_conflict"
    with closing(connect(public_db)) as conn:
        assert get_refund(conn, "C-001") is None


def test_lost_provider_response_is_recovered_by_query(public_db, tmp_path, monkeypatch):
    provider = Provider(tmp_path / "provider.sqlite", dedupe=False)
    real_refund = provider.refund
    def lost_response(key, amount):
        real_refund(key, amount)
        raise TimeoutError("simulated lost acknowledgement")
    monkeypatch.setattr(provider, "refund", lost_response)
    with pytest.raises(TimeoutError):
        pay(public_db, provider)
    monkeypatch.setattr(provider, "refund", real_refund)
    assert recover(public_db, provider)[0]["ok"]
    check_effects(public_db, provider, "C-001", 35000)


def test_failed_query_does_not_resend_an_unknown_payment(public_db, tmp_path, monkeypatch):
    provider = Provider(tmp_path / "provider.sqlite", dedupe=False)
    with pytest.raises(InjectedCrash):
        pay(public_db, provider, crash_at=POINTS[1])
    def unavailable(key):
        raise TimeoutError("simulated provider unavailable")
    with monkeypatch.context() as patch:
        patch.setattr(provider, "lookup", unavailable)
        with pytest.raises(TimeoutError):
            recover(public_db, provider)
    assert len(provider.lookup("refund:C-001")) == 1
    assert recover(public_db, provider)[0]["ok"]


def test_provider_dedupe_is_atomic_under_concurrent_calls(tmp_path):
    provider = Provider(tmp_path / "provider.sqlite")
    with ThreadPoolExecutor(max_workers=2) as pool:
        receipts = list(pool.map(lambda _: provider.refund("refund:C-001", 35000), range(2)))
    assert receipts[0] == receipts[1]
    assert len(provider.lookup("refund:C-001")) == 1


def test_concurrent_coordinators_share_one_claim_effect(public_db, tmp_path):
    provider = Provider(tmp_path / "provider.sqlite")
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: pay(public_db, provider), range(2)))
    assert all(row["ok"] for row in results)
    check_effects(public_db, provider, "C-001", 35000)


@pytest.mark.parametrize("point", ["before_effect", "after_effect_before_checkpoint", "after_checkpoint"])
def test_original_host_crash_points_remain_recoverable(public_db, tmp_path, point):
    provider = Provider(tmp_path / "provider.sqlite")
    with pytest.raises(InjectedCrash, match=point):
        pay(public_db, provider, crash_at=point)
    assert recover(public_db, provider)[0]["ok"]
    check_effects(public_db, provider, "C-001", 35000)


def test_evaluation_rejects_external_duplicates_even_when_local_contract_passes(tmp_path):
    from bonus.evaluate_provider import run_fault_trial
    row, _ = run_fault_trial(
        tmp_path / "evaluation", {"id": "PB-TEST", "claim_id": "C-001", "point": POINTS[1]}, 11,
        strategy="no_dedupe_retry",
    )
    assert not row["passed"] and row["reason"] == "provider_effect_mismatch"
    assert row["ledger_rows"] == row["host_audits"] == row["provider_audits"] == 1
    assert row["provider_effects"] == 2 and row["provider_total_vnd"] == 70000


@pytest.mark.parametrize("claim_id", list(BY_ID))
def test_bonus_shape_preserves_public_contract_and_safe_output(public_db, tmp_path, capsys, claim_id):
    provider = Provider(tmp_path / "provider.sqlite")
    result = run_with_provider(claim_id, seed=11, store_path=str(public_db), provider=provider)
    with closing(connect(public_db)) as conn:
        assert trial_pass(result.as_dict(), BY_ID[claim_id]["expected"], conn) == (True, "ok")
    trace = json.loads(Path(result.trace_path).read_text())
    assert trace["run_id"] == result.run_id
    assert result.model_calls == 0
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""
