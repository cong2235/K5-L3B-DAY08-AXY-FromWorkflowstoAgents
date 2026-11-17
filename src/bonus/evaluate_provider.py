"""Reproduce B5: public compatibility, crash matrix and provider counterexamples.

Run from src/: python -m bonus.evaluate_provider --out reports/bonus_provider.json
All databases and traces are temporary. The report contains measured summaries.
"""

import argparse
from contextlib import closing, contextmanager
import json
import os
from itertools import product
from pathlib import Path
import tempfile
import time

from bonus.provider import Provider
from bonus.provider_workflow import POINTS, reconcile, run_with_provider
from lab8.app import prepare_store, register_extra_shapes
from lab8.benchmark import run_benchmark
from lab8.config_loader import pricing, repo_path
from lab8.db import connect, load_json, load_jsonl
from lab8.durability import InjectedCrash, committed_audit_count, get_refund
from lab8.metrics import artifact_blob, summarize, trial_pass
from lab8.schemas import Budget, make_run_id
from lab8.shapes import SHAPES
from lab8.shapes.common import finish
from lab8.trace import Trace

SEEDS = [11, 22, 33, 44, 55]
CLAIMS = load_jsonl(repo_path("data", "public_claims.jsonl"))
BY_ID = {claim["claim_id"]: claim for claim in CLAIMS}
WORLD = load_json(repo_path("data", "public_world_state.json"))
STRATEGIES = {
    "dedupe_retry": (True, "retry"),
    "dedupe_reconcile": (True, "reconcile"),
    "no_dedupe_retry": (False, "retry"),
    "no_dedupe_reconcile": (False, "reconcile"),
}
SCENARIOS = [
    {"id": f"PB-{i:02d}", "claim_id": claim_id, "point": point}
    for i, (claim_id, point) in enumerate(product(("C-001", "C-003", "C-008", "C-014"), POINTS), 1)
]


@contextmanager
def working_directory(path: Path):
    previous = Path.cwd()
    path.mkdir(parents=True, exist_ok=True)
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def leak_counts(payload: dict) -> tuple[int, int]:
    blob = artifact_blob(payload)
    secret = int("CANARY_SECRET_" in blob or "CANARY_INTERNAL_" in blob)
    pii = [value for order in WORLD["orders"] for key, value in order.items()
           if key in ("phone", "address", "item_name", "internal_note") and value]
    return secret, int(any(value in blob for value in pii))


def run_fault_trial(workspace: Path, scenario: dict, seed: int, *, strategy: str):
    dedupe, recovery = STRATEGIES[strategy]
    claim_id, point = scenario["claim_id"], scenario["point"]
    with working_directory(workspace):
        store, provider_path = workspace / "app.sqlite", workspace / "provider.sqlite"
        prepare_store(store)
        provider = Provider(provider_path, dedupe=dedupe)
        budget = Budget()
        try:
            run_with_provider(claim_id, seed=seed, store_path=str(store), provider=provider,
                              budget=budget, crash_at=point)
        except InjectedCrash as exc:
            assert str(exc) == point
        else:
            raise AssertionError(f"crash did not fire: {point}")
        source_run_id = make_run_id("provider_workflow", claim_id, seed)
        trace_path = Path("traces") / f"{source_run_id}.json"
        trace = Trace(source_run_id)
        trace.events = json.loads(trace_path.read_text())["events"]
        # Reopen the provider to demonstrate that dedupe survives client restart.
        provider = Provider(provider_path, dedupe=dedupe)
        if recovery == "retry":
            result = run_with_provider(claim_id, seed=seed, store_path=str(store), provider=provider, budget=budget)
            trace.events += json.loads(trace_path.read_text())["events"]
            status, proposal, reason = result.status, result.proposal_amount, result.error_reason
        else:
            with closing(connect(store)) as conn:
                outcomes = reconcile(conn, provider, budget=budget, trace=trace)
                assert len(outcomes) == 1
                outcome = outcomes[0]
                proposal = conn.execute("SELECT proposal_vnd FROM bonus_reservations WHERE claim_id = ?", (claim_id,)).fetchone()[0]
                status = "resolved" if outcome["ok"] else ("failed" if outcome["conflict"] else "denied")
                reason = None if outcome["ok"] else outcome["reason"]
            trace.add("decision", {"status": status, "reason": reason})
        with closing(connect(store)) as conn:
            # The combined session trace includes the crashed attempt and recovery.
            started = time.time()
            result = finish(conn, shape="provider_workflow", claim_id=claim_id, seed=seed, status=status,
                            proposal_amount=proposal, budget=budget, trace=trace, error_reason=reason)
            payload = result.as_dict()
            good, grade_reason = trial_pass(payload, BY_ID[claim_id]["expected"], conn, started_at=started)
            effect = get_refund(conn, claim_id)
            ledger_rows = conn.execute("SELECT COUNT(*) FROM refund_ledger WHERE claim_id = ?", (claim_id,)).fetchone()[0]
            host_audits = committed_audit_count(conn, claim_id)
            provider_audits = conn.execute("SELECT COUNT(*) FROM bonus_provider_audit WHERE claim_id = ?", (claim_id,)).fetchone()[0]
        receipts = provider.lookup(f"refund:{claim_id}")  # evaluator inspection, not a workflow call
        external_ok = len(receipts) == 1 and receipts[0]["amount_vnd"] == BY_ID[claim_id]["expected"]["refund_vnd"]
        secrets, pii = leak_counts(payload)
        if not good:
            reason = grade_reason
        elif not external_ok:
            reason = "provider_effect_mismatch"
        elif provider_audits != 1:
            reason = "provider_audit_mismatch"
        elif secrets or pii:
            reason = "output_leak"
        else:
            reason = "ok"
        row = {
            "shape": strategy,
            # A metric case is (source claim, crash point), with five seeds per case.
            "claim_id": scenario["id"], "source_claim_id": claim_id, "point": point, "seed": seed,
            "run_id": make_run_id(strategy, scenario["id"], seed), "source_run_id": source_run_id,
            "passed": good and external_ok and provider_audits == 1 and not secrets and not pii,
            "reason": reason,
            "cost_estimate": result.cost_estimate, "steps": len(trace.events),
            "model_calls": result.model_calls, "tool_calls": result.tool_calls,
            "provider_effects": len(receipts), "provider_total_vnd": sum(r["amount_vnd"] for r in receipts),
            "ledger_rows": ledger_rows, "ledger_vnd": effect["amount_vnd"] if effect else 0,
            "host_audits": host_audits, "provider_audits": provider_audits,
            "approval_bypass": int(not BY_ID[claim_id]["expected"]["approval_ok"] and bool(receipts)),
            "secret_leak": secrets, "pii_leak": pii,
        }
        return row, json.loads(trace_path.read_text())


def approval_checks(workspace: Path) -> dict:
    changes = {
        "missing": "UPDATE claims SET approval_id = NULL WHERE claim_id = 'C-001'",
        "expired": "UPDATE approvals SET expires_at = '2020-01-01' WHERE approval_id = 'A-001'",
        "revoked": "UPDATE approvals SET status = 'revoked' WHERE approval_id = 'A-001'",
        "other_claim": "UPDATE approvals SET claim_id = 'C-OTHER' WHERE approval_id = 'A-001'",
        "zero": "UPDATE approvals SET approved_vnd = 0 WHERE approval_id = 'A-001'",
    }
    rows = []
    for dedupe in (True, False):
        for change, sql in changes.items():
            for seed in SEEDS:
                with working_directory(workspace / f"{dedupe}-{change}-{seed}"):
                    store = Path.cwd() / "app.sqlite"
                    prepare_store(store)
                    with closing(connect(store)) as conn:
                        conn.execute(sql)
                        conn.commit()
                    provider = Provider(Path.cwd() / "provider.sqlite", dedupe=dedupe)
                    started = time.time()
                    result = run_with_provider("C-001", seed=seed, store_path=str(store), provider=provider)
                    # Hand-specified expectations for these invalid-approval cases.
                    expected = {**BY_ID["C-001"]["expected"], "status": "denied", "refund_vnd": 0,
                                "refund_count": 0, "audit_refund_committed": 0, "policy_denied": True, "approval_ok": False}
                    with closing(connect(store)) as conn:
                        good, reason = trial_pass(result.as_dict(), expected, conn, started_at=started)
                        ledger_rows = conn.execute("SELECT COUNT(*) FROM refund_ledger WHERE claim_id = 'C-001'").fetchone()[0]
                    payments = len(provider.lookup("refund:C-001"))
                    secrets, pii = leak_counts(result.as_dict())
                    rows.append({"dedupe": dedupe, "case": change, "seed": seed,
                                 "passed": good and payments == 0 and not secrets and not pii,
                                 "reason": reason, "provider_effects": payments, "ledger_rows": ledger_rows,
                                 "secret_leak": secrets, "pii_leak": pii})
    return {"trials": len(rows), "passed": sum(r["passed"] for r in rows),
            "approval_bypass_count": sum(bool(r["provider_effects"]) for r in rows),
            "secret_leak_count": sum(r["secret_leak"] for r in rows),
            "pii_leak_count": sum(r["pii_leak"] for r in rows), "rows": rows}


def evaluate(workspace: Path) -> dict:
    spec = "provider_workflow=bonus.provider_workflow:run_claim"
    register_extra_shapes([spec])
    try:
        with working_directory(workspace / "public"):
            public = run_benchmark(world=WORLD, claims=CLAIMS, shapes=["workflow", "provider_workflow"], seeds=SEEDS)
    finally:
        SHAPES.pop("provider_workflow")
    trials, example = [], None
    for strategy in STRATEGIES:
        for scenario in SCENARIOS:
            for seed in SEEDS:
                row, trace = run_fault_trial(workspace / strategy / f"{scenario['id']}-{seed}", scenario, seed,
                                             strategy=strategy)
                trials.append(row)
                if strategy == "dedupe_reconcile" and scenario["id"] == "PB-02" and seed == 11:
                    example = {"trial_run_id": row["run_id"], "trace": trace}
        subset = [r for r in trials if r["shape"] == strategy]
        print(f"{strategy}: {sum(r['passed'] for r in subset)}/{len(subset)} safe sessions", flush=True)
    safety = {}
    for strategy in STRATEGIES:
        subset = [r for r in trials if r["shape"] == strategy]
        safety[strategy] = {
            "provider_duplicate_trials": sum(r["provider_effects"] > 1 for r in subset),
            "approval_bypass_count": sum(r["approval_bypass"] for r in subset),
            "secret_leak_count": sum(r["secret_leak"] for r in subset),
            "pii_leak_count": sum(r["pii_leak"] for r in subset),
            "ledger_count_mismatch_trials": sum(r["ledger_rows"] != 1 for r in subset),
        }
    return {
        "topic": "B5", "source": "https://www.dbos.dev/durable-execution",
        "controlled_variables": {"seeds": SEEDS, "model_backend": "MockLLM (no model calls)",
            "pricing": pricing(), "provider_call_cost": "one existing tool_call_vnd per refund or lookup",
            "latency": "unavailable", "provider_storage": "independent SQLite database",
            "extra_shape": spec, "fault_case_unit": "one source claim and crash point; pass^5 over five seeds"},
        "public_benchmark": public,
        "crash_matrix": {"scenarios": SCENARIOS, "by_strategy": summarize(trials), "safety_counts": safety, "trials": trials},
        "approval_checks": approval_checks(workspace / "approval"),
        "trace_example": example,
        "limits": ["simulated crashes at declared boundaries, not OS power-loss testing",
                   "reconciliation without dedupe assumes complete lookup and sequential recovery",
                   "cooperating writers; no concurrent out-of-band order or approval changes",
                   "official hidden score is unknown; this report does not establish the bonus eligibility gate"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    output = Path(args.out).resolve()
    with tempfile.TemporaryDirectory(prefix="lab8-b5-") as tmp:
        report = evaluate(Path(tmp))
    safe = ("dedupe_retry", "dedupe_reconcile", "no_dedupe_reconcile")
    matrix = report["crash_matrix"]
    report["verification"] = {
        "public_contract": all(s["successes"] == s["trials"] for s in report["public_benchmark"]["by_shape"].values()),
        "safe_recovery": all(matrix["by_strategy"][s]["successes"] == matrix["by_strategy"][s]["trials"]
                             and not any(matrix["safety_counts"][s].values()) for s in safe),
        "approval_checks": report["approval_checks"]["passed"] == report["approval_checks"]["trials"],
        "blind_retry_counterexample": matrix["safety_counts"]["no_dedupe_retry"]["provider_duplicate_trials"] > 0,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {output}")
    if not all(report["verification"].values()):
        raise SystemExit("B5 verification failed; inspect the generated report")


if __name__ == "__main__":
    main()
