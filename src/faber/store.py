"""Minimal local SQLite store skeleton."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from faber.canonical_json import canonical_json
from faber.trajectories import Trajectory

SCHEMA_SQL = """
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
    return store_path


def write_trajectory(path: str | Path, trajectory: Trajectory) -> None:
    store_path = init_local_store(path)
    payload = canonical_json(trajectory.to_dict())
    with sqlite3.connect(store_path) as connection:
        connection.execute(
            """
            insert or replace into trajectories (id, digest, created_at, payload)
            values (?, ?, ?, ?)
            """,
            (trajectory.id, trajectory.digest(), trajectory.created_at, payload),
        )
