"""Offline B5 provider. Its database commits independently of the application."""

from contextlib import closing
from pathlib import Path
import sqlite3


class ProviderConflict(ValueError):
    """An idempotency key was reused with a different amount."""


class Provider:
    def __init__(self, store_path: str | Path, *, dedupe: bool = True):
        self.store_path = str(Path(store_path).resolve())
        self.dedupe = dedupe
        Path(self.store_path).parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS provider_refunds (
                    receipt_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_key TEXT NOT NULL,
                    dedupe_key TEXT UNIQUE,
                    amount_vnd INTEGER NOT NULL CHECK (amount_vnd > 0)
                );
            """)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.store_path)
        conn.row_factory = sqlite3.Row
        return conn

    def refund(self, key: str, amount_vnd: int) -> dict:
        if not key or amount_vnd <= 0:
            raise ValueError("refund requires a key and a positive amount")
        with closing(self._connect()) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute(
                "SELECT receipt_id, request_key, amount_vnd FROM provider_refunds WHERE request_key = ?",
                (key,),
            ).fetchone()
            if self.dedupe and existing is not None:
                if existing["amount_vnd"] != amount_vnd:
                    raise ProviderConflict("idempotency key amount conflict")
                return dict(existing)
            inserted = conn.execute(
                "INSERT INTO provider_refunds (request_key, dedupe_key, amount_vnd) VALUES (?, ?, ?)",
                (key, key if self.dedupe else None, amount_vnd),
            )
            return {"receipt_id": inserted.lastrowid, "request_key": key, "amount_vnd": amount_vnd}

    def lookup(self, key: str) -> list[dict]:
        with closing(self._connect()) as conn:
            return [dict(row) for row in conn.execute(
                "SELECT receipt_id, request_key, amount_vnd FROM provider_refunds WHERE request_key = ? ORDER BY receipt_id",
                (key,),
            )]
