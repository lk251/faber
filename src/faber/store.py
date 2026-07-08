"""Local SQLite store for canonical Faber protocol records."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from faber.attempts import Attempt
from faber.canonical_json import canonical_json
from faber.contracts import TaskContract
from faber.errors import ValidationError
from faber.events import MarketEvent
from faber.receipts import VerificationReceipt
from faber.routing import RouterDecision
from faber.settlement import Settlement
from faber.trajectories import Trajectory
from faber.verifiers import VerifierRun
from faber.workers import WorkerProfile


class ProtocolRecord(Protocol):
    @property
    def id(self) -> str: ...

    @property
    def created_at(self) -> str: ...

    def to_dict(self) -> dict[str, object]: ...

    def digest(self) -> str: ...


@dataclass(frozen=True)
class SavedRecord:
    record_type: str
    record_id: str
    digest: str
    inserted: bool


SCHEMA_VERSION = 1

SCHEMA_SQL = """
create table if not exists schema_version (
  version integer primary key,
  applied_at text not null default current_timestamp
);

create table if not exists records (
  record_type text not null,
  id text not null,
  digest text not null,
  created_at text not null,
  payload text not null,
  primary key (record_type, id),
  unique (record_type, digest)
);

create table if not exists lifecycle_events (
  sequence integer primary key autoincrement,
  event_id text not null unique,
  event_type text not null,
  subject_id text not null,
  created_at text not null,
  digest text not null,
  payload text not null
);

create table if not exists trajectories (
  id text primary key,
  digest text not null,
  created_at text not null,
  payload text not null
);

create table if not exists market_events (
  id text primary key,
  event_type text not null,
  created_at text not null,
  payload text not null
);
"""


def init_local_store(path: str | Path) -> Path:
    store_path = Path(path)
    store_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(store_path) as connection:
        connection.executescript(SCHEMA_SQL)
        connection.execute(
            "insert or ignore into schema_version (version) values (?)",
            (SCHEMA_VERSION,),
        )
    return store_path


def _connect(path: str | Path) -> sqlite3.Connection:
    store_path = init_local_store(path)
    connection = sqlite3.connect(store_path)
    connection.row_factory = sqlite3.Row
    return connection


def save_record(path: str | Path, record_type: str, record: ProtocolRecord) -> SavedRecord:
    if not record_type:
        raise ValidationError("record_type must be a non-empty string")
    payload = canonical_json(record.to_dict())
    digest = record.digest()
    with _connect(path) as connection:
        existing = connection.execute(
            "select digest from records where record_type = ? and id = ?",
            (record_type, record.id),
        ).fetchone()
        if existing is not None:
            if existing["digest"] != digest:
                raise ValidationError(
                    f"{record_type} record {record.id} already exists with a different digest"
                )
            return SavedRecord(record_type, record.id, digest, inserted=False)
        duplicate_digest = connection.execute(
            "select id from records where record_type = ? and digest = ?",
            (record_type, digest),
        ).fetchone()
        if duplicate_digest is not None:
            return SavedRecord(record_type, duplicate_digest["id"], digest, inserted=False)
        connection.execute(
            """
            insert into records (record_type, id, digest, created_at, payload)
            values (?, ?, ?, ?, ?)
            """,
            (record_type, record.id, digest, record.created_at, payload),
        )
        if record_type == "trajectory":
            connection.execute(
                """
                insert or ignore into trajectories (id, digest, created_at, payload)
                values (?, ?, ?, ?)
                """,
                (record.id, digest, record.created_at, payload),
            )
        return SavedRecord(record_type, record.id, digest, inserted=True)


def load_record(path: str | Path, record_type: str, record_id: str) -> dict[str, object] | None:
    with _connect(path) as connection:
        row = connection.execute(
            "select payload from records where record_type = ? and id = ?",
            (record_type, record_id),
        ).fetchone()
    if row is None:
        return None
    payload = json.loads(row["payload"])
    if not isinstance(payload, dict):
        raise ValidationError("stored record payload must be a JSON object")
    return payload


def list_records(path: str | Path, record_type: str) -> list[dict[str, object]]:
    with _connect(path) as connection:
        rows = connection.execute(
            """
            select id, digest, created_at, payload from records
            where record_type = ?
            order by created_at, id
            """,
            (record_type,),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "digest": row["digest"],
            "created_at": row["created_at"],
            "payload": json.loads(row["payload"]),
        }
        for row in rows
    ]


def save_lifecycle_event(path: str | Path, event: MarketEvent) -> int:
    payload = canonical_json(event.to_dict())
    digest = event.digest()
    with _connect(path) as connection:
        existing = connection.execute(
            "select sequence, digest from lifecycle_events where event_id = ?",
            (event.id,),
        ).fetchone()
        if existing is not None:
            if existing["digest"] != digest:
                raise ValidationError(
                    f"lifecycle event {event.id} already exists with a different digest"
                )
            return int(existing["sequence"])
        cursor = connection.execute(
            """
            insert into lifecycle_events
              (event_id, event_type, subject_id, created_at, digest, payload)
            values (?, ?, ?, ?, ?, ?)
            """,
            (event.id, event.event_type, event.subject_id, event.created_at, digest, payload),
        )
        connection.execute(
            """
            insert or ignore into market_events (id, event_type, created_at, payload)
            values (?, ?, ?, ?)
            """,
            (event.id, event.event_type, event.created_at, payload),
        )
        if cursor.lastrowid is None:
            raise ValidationError("failed to append lifecycle event")
        return int(cursor.lastrowid)


def list_lifecycle_events(path: str | Path) -> list[dict[str, object]]:
    with _connect(path) as connection:
        rows = connection.execute(
            """
            select sequence, event_id, event_type, subject_id, created_at, digest, payload
            from lifecycle_events
            order by sequence
            """
        ).fetchall()
    return [
        {
            "sequence": row["sequence"],
            "event_id": row["event_id"],
            "event_type": row["event_type"],
            "subject_id": row["subject_id"],
            "created_at": row["created_at"],
            "digest": row["digest"],
            "payload": json.loads(row["payload"]),
        }
        for row in rows
    ]


def store_summary(path: str | Path) -> dict[str, object]:
    with _connect(path) as connection:
        record_rows = connection.execute(
            "select record_type, count(*) as count from records group by record_type"
        ).fetchall()
        event_count = connection.execute(
            "select count(*) as count from lifecycle_events"
        ).fetchone()
    return {
        "schema_version": SCHEMA_VERSION,
        "record_counts": {row["record_type"]: row["count"] for row in record_rows},
        "lifecycle_event_count": event_count["count"] if event_count is not None else 0,
    }


def export_trajectory(path: str | Path, trajectory_id: str, out_path: str | Path) -> Path:
    payload = load_record(path, "trajectory", trajectory_id)
    if payload is None:
        raise ValidationError(f"trajectory {trajectory_id} not found")
    output = Path(out_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(canonical_json(payload) + "\n", encoding="utf-8")
    return output


def save_task_contract(path: str | Path, record: TaskContract) -> SavedRecord:
    return save_record(path, "task_contract", record)


def save_attempt(path: str | Path, record: Attempt) -> SavedRecord:
    return save_record(path, "attempt", record)


def save_verifier_run(path: str | Path, record: VerifierRun) -> SavedRecord:
    return save_record(path, "verifier_run", record)


def save_verification_receipt(path: str | Path, record: VerificationReceipt) -> SavedRecord:
    return save_record(path, "verification_receipt", record)


def save_trajectory(path: str | Path, record: Trajectory) -> SavedRecord:
    return save_record(path, "trajectory", record)


def save_settlement(path: str | Path, record: Settlement) -> SavedRecord:
    return save_record(path, "settlement", record)


def save_worker_profile(path: str | Path, record: WorkerProfile) -> SavedRecord:
    return save_record(path, "worker_profile", record)


def save_router_decision(path: str | Path, record: RouterDecision) -> SavedRecord:
    return save_record(path, "router_decision", record)


def save_market_event(path: str | Path, record: MarketEvent) -> int:
    return save_lifecycle_event(path, record)


def write_trajectory(path: str | Path, trajectory: Trajectory) -> None:
    save_trajectory(path, trajectory)
