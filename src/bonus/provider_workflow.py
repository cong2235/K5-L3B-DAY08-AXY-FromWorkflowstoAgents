"""B5 coordinator: durable intent, independent provider, then the unchanged host.

The host still commits refund_ledger and refund_committed atomically. The final
bonus_provider_audit is a separate reconciliation acknowledgement, not a split
of the host transaction. Each store uses one fixed provider. Cooperating writers
serialize pending claims per order.
"""

from pathlib import Path
import sqlite3

from bonus.provider import Provider, ProviderConflict
from lab8.db import connect
from lab8.durability import InjectedCrash, get_refund, idempotency_key, issue_refund, record_policy_denied
from lab8.policy import AuthDecision, authorize, order_refunded_vnd
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish
from lab8.tools import compute_compensation, get_claim_view, lookup_order, tool_cost
from lab8.trace import Trace

POINTS = (
    "after_reserve_before_provider",
    "after_provider_before_confirm",
    "after_confirm_before_audit",
)


def _schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS bonus_reservations (
            claim_id TEXT PRIMARY KEY, order_id TEXT NOT NULL,
            proposal_vnd INTEGER NOT NULL, amount_vnd INTEGER NOT NULL,
            receipt_id INTEGER,
            state TEXT NOT NULL CHECK (state IN ('reserved', 'confirmed'))
        );
        CREATE UNIQUE INDEX IF NOT EXISTS bonus_pending_order
            ON bonus_reservations(order_id) WHERE state = 'reserved';
        CREATE TABLE IF NOT EXISTS bonus_provider_audit (
            claim_id TEXT PRIMARY KEY, receipt_id INTEGER NOT NULL,
            amount_vnd INTEGER NOT NULL
        );
    """)


def _failure(reason: str, *, conflict: bool = False) -> dict:
    return {"ok": False, "reason": reason, "conflict": conflict}


def _authorization(conn, claim_id: str, proposal: int) -> tuple[str | None, AuthDecision]:
    row = conn.execute("""
        SELECT c.order_id, c.principal_id AS claimant, o.principal_id AS owner, o.paid_vnd
        FROM claims c LEFT JOIN orders o ON o.order_id = c.order_id WHERE c.claim_id = ?
    """, (claim_id,)).fetchone()
    reason = None
    if row is None:
        reason = "unknown_claim"
    elif not row["order_id"]:
        reason = "missing_order"
    elif row["owner"] != row["claimant"]:
        reason = "outside_principal_scope"
    if reason:
        return None, AuthDecision(False, reason, 0, 0, None)
    already = order_refunded_vnd(conn, row["order_id"], exclude_claim_id=claim_id)
    return row["order_id"], authorize(
        conn, claim_id, proposal, paid_vnd=row["paid_vnd"], already_refunded_vnd=already,
    )


def _reserve(conn, claim_id: str, proposal: int) -> dict:
    _schema(conn)
    with conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM bonus_reservations WHERE claim_id = ?", (claim_id,)).fetchone()
        if row:
            if row["proposal_vnd"] != proposal:
                return _failure("amount_conflict", conflict=True)
            if row["state"] == "confirmed":
                return {"ok": True, "reservation": dict(row)}
        elif get_refund(conn, claim_id) is not None:
            return _failure("unmanaged_refund", conflict=True)
        order_id, decision = _authorization(conn, claim_id, proposal)
        if not decision.ok:
            record_policy_denied(conn, claim_id, decision.reason)
            return _failure(decision.reason)
        if row and row["amount_vnd"] != decision.amount_vnd:
            return _failure("amount_conflict", conflict=True)
        pending = conn.execute(
            "SELECT claim_id FROM bonus_reservations WHERE order_id = ? AND state = 'reserved' AND claim_id != ?",
            (order_id, claim_id),
        ).fetchone()
        if pending:
            return _failure("order_pending", conflict=True)
        if row is None:
            conn.execute("""
                INSERT INTO bonus_reservations
                (claim_id, order_id, proposal_vnd, amount_vnd, state)
                VALUES (?, ?, ?, ?, 'reserved')
            """, (claim_id, order_id, proposal, decision.amount_vnd))
            row = conn.execute("SELECT * FROM bonus_reservations WHERE claim_id = ?", (claim_id,)).fetchone()
        return {"ok": True, "reservation": dict(row)}


def _confirm(conn, reservation: dict, receipt: dict, *, crash_at=None, trace=None) -> dict:
    claim_id = reservation["claim_id"]
    if receipt["request_key"] != idempotency_key(claim_id) or receipt["amount_vnd"] != reservation["amount_vnd"]:
        return _failure("provider_amount_conflict", conflict=True)
    effect = get_refund(conn, claim_id)
    if effect is None:
        _, decision = _authorization(conn, claim_id, reservation["proposal_vnd"])
        if not decision.ok:
            record_policy_denied(conn, claim_id, decision.reason)
            return _failure(decision.reason)
        if decision.amount_vnd != reservation["amount_vnd"]:
            return _failure("amount_conflict", conflict=True)
        outcome = issue_refund(
            conn, claim_id, reservation["proposal_vnd"],
            crash_at=crash_at if crash_at not in POINTS else None,
        )
        if not outcome["ok"]:
            return outcome
        effect = outcome["effect"]
    if effect["amount_vnd"] != receipt["amount_vnd"]:
        return _failure("amount_conflict", conflict=True)
    conn.execute(
        "UPDATE bonus_reservations SET state = 'confirmed', receipt_id = ? WHERE claim_id = ?",
        (receipt["receipt_id"], claim_id),
    )
    conn.commit()
    if trace is not None:
        trace.add("ledger_confirmed", {"amount_vnd": effect["amount_vnd"]})
    if crash_at == "after_confirm_before_audit":
        raise InjectedCrash(crash_at)
    conn.execute(
        "INSERT OR IGNORE INTO bonus_provider_audit VALUES (?, ?, ?)",
        (claim_id, receipt["receipt_id"], receipt["amount_vnd"]),
    )
    conn.commit()
    if trace is not None:
        trace.add("provider_audited", {"receipt_id": receipt["receipt_id"]})
    return {"ok": True, "reason": "confirmed", "conflict": False, "effect": effect}


def pay_refund(conn, claim_id, proposal, provider, *, budget=None, crash_at=None, trace=None):
    """Retry by key. Without provider dedupe, a lost acknowledgement can double pay."""
    budget = budget if budget is not None else Budget()
    reserved = _reserve(conn, claim_id, proposal)
    if not reserved["ok"]:
        return reserved
    reservation = reserved["reservation"]
    if reservation["state"] == "confirmed":
        receipt = {"request_key": idempotency_key(claim_id), "receipt_id": reservation["receipt_id"], "amount_vnd": reservation["amount_vnd"]}
        return _confirm(conn, reservation, receipt, trace=trace)
    if trace is not None:
        trace.add("reserved", {"claim_id": claim_id, "amount_vnd": reservation["amount_vnd"]})
    if crash_at == "after_reserve_before_provider":
        raise InjectedCrash(crash_at)
    budget.add_tool(tool_cost())
    try:
        receipt = provider.refund(idempotency_key(claim_id), reservation["amount_vnd"])
    except ProviderConflict:
        return _failure("provider_amount_conflict", conflict=True)
    if trace is not None:
        trace.add("provider_refunded", {"receipt_id": receipt["receipt_id"], "amount_vnd": receipt["amount_vnd"]})
    if crash_at == "after_provider_before_confirm":
        raise InjectedCrash(crash_at)
    return _confirm(conn, reservation, receipt, crash_at=crash_at, trace=trace)


def reconcile(conn, provider, *, budget=None, trace=None):
    """Query the provider before deciding whether a pending intent needs a send.

    Lookup must be complete and consistent. Provider errors stop the job, leaving
    reservations for a later run. Ambiguous history or changed approval can
    require review; this is not a distributed transaction.
    """
    _schema(conn)
    budget = budget if budget is not None else Budget()
    pending = conn.execute("""
        SELECT r.* FROM bonus_reservations r
        LEFT JOIN bonus_provider_audit a ON a.claim_id = r.claim_id
        WHERE r.state = 'reserved' OR a.claim_id IS NULL ORDER BY r.claim_id
    """).fetchall()
    outcomes = []
    for row in pending:
        reservation = dict(row)
        budget.add_tool(tool_cost())
        receipts = provider.lookup(idempotency_key(row["claim_id"]))
        if trace is not None:
            trace.add("provider_lookup", {"claim_id": row["claim_id"], "matches": len(receipts)})
        if len(receipts) > 1:
            outcome = _failure("provider_ambiguous", conflict=True)
        elif receipts:
            outcome = _confirm(conn, reservation, receipts[0], trace=trace)
        elif row["state"] == "confirmed":
            outcome = _failure("provider_missing_receipt", conflict=True)
        else:
            outcome = pay_refund(conn, row["claim_id"], row["proposal_vnd"], provider, budget=budget, trace=trace)
        outcomes.append({"claim_id": row["claim_id"], **outcome})
    return outcomes


def run_with_provider(claim_id, *, seed, store_path, provider, budget=None, crash_at=None) -> RunResult:
    conn = connect(store_path)
    budget = budget if budget is not None else Budget()
    trace = Trace(make_run_id("provider_workflow", claim_id, seed))
    proposal = 0
    try:
        budget.add_tool(tool_cost())
        claim = get_claim_view(conn, claim_id)
        trace.add("claim_lookup", {"found": claim["found"]})
        if not claim["found"]:
            status, reason = "failed", "unknown_claim"
        elif not claim["order_id"]:
            status, reason = "needs_info", "missing_order_id"
        else:
            budget.add_tool(tool_cost())
            order = lookup_order(conn, claim["order_id"], claim["principal_id"])
            trace.add("order_lookup", {"visible": order["visible"], "reason": order["reason"]})
            if not order["visible"]:
                status, reason = "escalated", order["reason"]
            else:
                budget.add_tool(tool_cost())
                quote = compute_compensation(conn, order["order"])
                proposal = int(quote["amount_vnd"])
                trace.add("quote", quote)
                if proposal <= 0:
                    status, reason = "denied", quote["reason"]
                else:
                    trace.add("provider_requested", {"proposal_amount": proposal})
                    trace.write()
                    outcome = pay_refund(conn, claim_id, proposal, provider, budget=budget, crash_at=crash_at, trace=trace)
                    trace.add("provider_outcome", {"ok": outcome["ok"], "reason": outcome["reason"]})
                    status = "resolved" if outcome["ok"] else ("failed" if outcome["conflict"] else "denied")
                    reason = None if outcome["ok"] else outcome["reason"]
        trace.add("decision", {"status": status, "reason": reason})
        return finish(conn, shape="provider_workflow", claim_id=claim_id, seed=seed, status=status,
                      proposal_amount=proposal, budget=budget, trace=trace, error_reason=reason)
    except InjectedCrash:
        trace.add("crash", {"at": crash_at})
        trace.write()
        raise
    finally:
        conn.close()


def run_claim(claim_id: str, *, seed: int, store_path: str, crash_at: str | None = None) -> RunResult:
    provider = Provider(Path(store_path).with_suffix(".provider.sqlite"))
    return run_with_provider(claim_id, seed=seed, store_path=store_path, provider=provider, crash_at=crash_at)
