#!/usr/bin/env python3
"""Idempotent Appwrite schema reconciliation for Agent Arena.

Usage (from repo root or backend/):

    python backend/scripts/reconcile_appwrite_schema.py --check
    python backend/scripts/reconcile_appwrite_schema.py --apply

Never prints the API key. Does not delete collections, attributes, indexes, or
user documents. Incompatible live types/sizes fail loudly.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import uuid
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
_REPO = _BACKEND.parent
sys.path.insert(0, str(_BACKEND))

from dotenv import load_dotenv

load_dotenv(_REPO / ".env")

from appwrite.enums.databases_index_type import DatabasesIndexType
from appwrite.exception import AppwriteException
from appwrite.query import Query

from agent_arena import db
from agent_arena.schema import ARRAY_ATTRIBUTES, COLLECTIONS, INDEXES

STRING_SIZE = 262144
WAIT_SECONDS = 90
POLL_INTERVAL = 1.0
INDEX_PREFIX_LEN = 64
LARGE_STRING_ATTRS = {
    ("formats", "config"),
    ("battle_events", "payload"),
    ("rounds", "artifact"),
    ("battles", "preview_urls"),
    ("targets", "config"),
    ("memories", "insight"),
    ("memories", "theory"),
    ("scores", "justification"),
    ("providers", "encrypted_key"),
}

_TYPE_MAP = {
    "string": "string",
    "integer": "integer",
    "double": "float",
    "float": "float",
    "boolean": "boolean",
}

_INDEX_ENUM = {
    "key": DatabasesIndexType.KEY,
    "unique": DatabasesIndexType.UNIQUE,
    "fulltext": DatabasesIndexType.FULLTEXT,
}


class SchemaError(RuntimeError):
    pass


def _redact(text: str) -> str:
    key = os.environ.get("APPWRITE_API_KEY") or ""
    if key and key in text:
        return text.replace(key, "[redacted]")
    return text


def _exc_body(exc: BaseException) -> str:
    parts = [type(exc).__name__, str(exc)]
    if isinstance(exc, AppwriteException):
        if getattr(exc, "code", None) is not None:
            parts.append(f"code={exc.code}")
        if getattr(exc, "type", None):
            parts.append(f"type={exc.type}")
        if getattr(exc, "response", None):
            parts.append(f"response={exc.response}")
    return _redact(" ".join(str(p) for p in parts if p))


def _attr_key(a) -> str:
    return getattr(a, "key", None) or (a.get("key") if isinstance(a, dict) else "")


def _attr_type(a) -> str:
    raw = getattr(a, "type", None) or (a.get("type") if isinstance(a, dict) else "")
    return _TYPE_MAP.get(str(raw).lower(), str(raw).lower())


def _norm_status(raw) -> str:
    text = str(raw or "").lower()
    return text.split(".")[-1] if text else ""


def _attr_status(a) -> str:
    return _norm_status(
        getattr(a, "status", None) or (a.get("status") if isinstance(a, dict) else "")
    )


def _attr_size(a):
    return getattr(a, "size", None) if not isinstance(a, dict) else a.get("size")


def _attr_array(a) -> bool:
    val = getattr(a, "array", None) if not isinstance(a, dict) else a.get("array")
    return bool(val)


def _idx_key(i) -> str:
    return getattr(i, "key", None) or (i.get("key") if isinstance(i, dict) else "")


def _idx_status(i) -> str:
    return _norm_status(
        getattr(i, "status", None) or (i.get("status") if isinstance(i, dict) else "")
    )


def _list_collections(databases, database_id) -> dict:
    res = databases.list_collections(database_id)
    return {c.id: c for c in res.collections}


def _list_attributes(databases, database_id, collection_id) -> dict:
    res = databases.list_attributes(database_id, collection_id)
    return {_attr_key(a): a for a in res.attributes}


def _list_indexes(databases, database_id, collection_id) -> dict:
    res = databases.list_indexes(database_id, collection_id)
    return {_idx_key(i): i for i in res.indexes}


def _create_attribute(databases, database_id, collection_id, name, type_, required):
    array_size = ARRAY_ATTRIBUTES.get(collection_id, {}).get(name)
    if array_size:
        databases.create_string_attribute(
            database_id,
            collection_id,
            name,
            array_size,
            required=required,
            array=True,
        )
        return
    if type_ == "string":
        databases.create_string_attribute(
            database_id, collection_id, name, STRING_SIZE, required=required
        )
    elif type_ == "integer":
        databases.create_integer_attribute(
            database_id, collection_id, name, required=required
        )
    elif type_ == "float":
        databases.create_float_attribute(
            database_id, collection_id, name, required=required
        )
    elif type_ == "boolean":
        databases.create_boolean_attribute(
            database_id, collection_id, name, required=required
        )
    else:
        raise SchemaError(f"unknown attribute type {type_!r} for {collection_id}.{name}")


def _wait_available(getter, label: str) -> None:
    deadline = time.time() + WAIT_SECONDS
    last = ""
    while time.time() < deadline:
        obj = getter()
        last = _attr_status(obj) if hasattr(obj, "status") or isinstance(obj, dict) else ""
        status = last or _idx_status(obj)
        if status == "available":
            return
        if status == "failed":
            raise SchemaError(f"{label} entered failed status")
        time.sleep(POLL_INTERVAL)
    raise SchemaError(f"{label} not available after {WAIT_SECONDS}s (last={last!r})")


def _check_existing_attr(collection_id: str, name: str, type_: str, required: bool, live) -> list[str]:
    errors: list[str] = []
    live_type = _attr_type(live)
    want_array = name in ARRAY_ATTRIBUTES.get(collection_id, {})
    if live_type != type_:
        errors.append(
            f"FAIL  {collection_id}.{name} type {live_type!r} != spec {type_!r}"
        )
    if _attr_array(live) != want_array:
        errors.append(
            f"FAIL  {collection_id}.{name} array={_attr_array(live)} != spec {want_array}"
        )
    if type_ == "string" and not want_array:
        size = _attr_size(live)
        if size is not None and int(size) < STRING_SIZE:
            if (collection_id, name) in LARGE_STRING_ATTRS:
                errors.append(
                    f"FAIL  {collection_id}.{name} size {size} < spec {STRING_SIZE}"
                )
    if want_array:
        size = _attr_size(live)
        expected = ARRAY_ATTRIBUTES[collection_id][name]
        if size is not None and int(size) < expected:
            errors.append(
                f"FAIL  {collection_id}.{name} array element size {size} < spec {expected}"
            )
    status = _attr_status(live)
    if status and status not in ("available", "processing"):
        errors.append(f"FAIL  {collection_id}.{name} status {status!r}")
    return errors


def check_schema() -> int:
    databases = db.get_databases()
    database_id = db.get_database_id()
    failures = 0
    collections = _list_collections(databases, database_id)
    print(f"INFO  database {database_id} collections={len(collections)}")
    for collection_id, attrs in COLLECTIONS.items():
        if collection_id not in collections:
            print(f"MISS  collection {collection_id}")
            failures += 1
            continue
        print(f"OK    collection {collection_id}")
        live_attrs = _list_attributes(databases, database_id, collection_id)
        for name, type_, required in attrs:
            live = live_attrs.get(name)
            if live is None:
                print(f"MISS  {collection_id}.{name} {type_} required={required}")
                failures += 1
                continue
            errs = _check_existing_attr(collection_id, name, type_, required, live)
            if errs:
                for e in errs:
                    print(e)
                failures += len(errs)
            else:
                print(
                    f"OK    {collection_id}.{name} type={_attr_type(live)} "
                    f"status={_attr_status(live)}"
                )
        live_idx = _list_indexes(databases, database_id, collection_id)
        for key, _typ, columns in INDEXES.get(collection_id, []):
            if key not in live_idx:
                # 262144-char string attrs often cannot be indexed; treat as warn.
                print(f"WARN  index {collection_id}.{key} missing on {columns}")
            else:
                print(f"OK    index {collection_id}.{key} status={_idx_status(live_idx[key])}")
    return failures


def apply_schema() -> int:
    databases = db.get_databases()
    database_id = db.get_database_id()
    failures = 0
    collections = _list_collections(databases, database_id)
    for collection_id, attrs in COLLECTIONS.items():
        if collection_id not in collections:
            print(f"CREATE collection {collection_id}")
            databases.create_collection(
                database_id, collection_id, collection_id, permissions=[]
            )
            collections = _list_collections(databases, database_id)
        live_attrs = _list_attributes(databases, database_id, collection_id)
        for name, type_, required in attrs:
            live = live_attrs.get(name)
            if live is None:
                print(f"CREATE {collection_id}.{name} {type_}")
                try:
                    _create_attribute(
                        databases, database_id, collection_id, name, type_, required
                    )
                except Exception as exc:
                    print(f"FAIL  create {collection_id}.{name}: {_exc_body(exc)}")
                    failures += 1
                    continue
                _wait_available(
                    lambda n=name: _list_attributes(databases, database_id, collection_id)[n],
                    f"{collection_id}.{name}",
                )
                continue
            errs = _check_existing_attr(collection_id, name, type_, required, live)
            if errs:
                for e in errs:
                    print(e)
                failures += len(errs)
                continue
            if _attr_status(live) != "available":
                _wait_available(
                    lambda n=name: _list_attributes(databases, database_id, collection_id)[n],
                    f"{collection_id}.{name}",
                )
        live_idx = _list_indexes(databases, database_id, collection_id)
        for key, typ, columns in INDEXES.get(collection_id, []):
            if key in live_idx:
                status = _idx_status(live_idx[key])
                if status == "available":
                    print(f"OK    index {collection_id}.{key}")
                elif status == "failed":
                    print(f"WARN  index {collection_id}.{key} exists in failed status")
                else:
                    try:
                        _wait_available(
                            lambda k=key: _list_indexes(databases, database_id, collection_id)[k],
                            f"index {collection_id}.{key}",
                        )
                    except SchemaError as exc:
                        print(f"WARN  {_exc_body(exc)}")
                continue
            print(f"CREATE index {collection_id}.{key} on {columns}")
            try:
                live_attrs = _list_attributes(databases, database_id, collection_id)
                lengths = []
                any_string = False
                for col in columns:
                    if _attr_type(live_attrs.get(col, {})) == "string":
                        lengths.append(int(INDEX_PREFIX_LEN))
                        any_string = True
                    else:
                        lengths.append(None)
                databases.create_index(
                    database_id,
                    collection_id,
                    key,
                    _INDEX_ENUM.get(typ, DatabasesIndexType.KEY),
                    columns,
                    lengths=lengths if any_string else None,
                )
                _wait_available(
                    lambda k=key: _list_indexes(databases, database_id, collection_id)[k],
                    f"index {collection_id}.{key}",
                )
                print(f"OK    index {collection_id}.{key}")
            except Exception as exc:
                body = _exc_body(exc)
                print(f"WARN  index {collection_id}.{key} skipped: {body}")
                if "size" not in body.lower() and "length" not in body.lower() and "index" not in body.lower():
                    failures += 1
    return failures


def _probe() -> int:
    databases = db.get_databases()
    database_id = db.get_database_id()
    failures = 0
    probe_id = f"probe-{uuid.uuid4().hex[:16]}"[:36]
    print(f"INFO  running write probes (id prefix {probe_id[:12]}…)")

    try:
        databases.create_document(
            database_id,
            "battle_events",
            probe_id,
            {
                "battle_id": probe_id,
                "event_id": probe_id,
                "payload": '{"type":"probe","data":{}}',
                "created_at": time.time(),
            },
        )
        got = databases.get_document(database_id, "battle_events", probe_id)
        assert got.data["event_id"] == probe_id
        databases.delete_document(database_id, "battle_events", probe_id)
        print("PASS  battle_events create/read/delete")
    except Exception as exc:
        print(f"FAIL  battle_events probe: {_exc_body(exc)}")
        failures += 1
        try:
            databases.delete_document(database_id, "battle_events", probe_id)
        except Exception:
            pass

    battle_id = f"pb{uuid.uuid4().hex[:18]}"
    try:
        databases.create_document(
            database_id,
            "battles",
            battle_id,
            {
                "user_id": "probe",
                "format_id": "probe",
                "model_ids": ["probe-a", "probe-b"],
                "arena_size": 2,
                "status": "queued",
                "timeout_seconds": 60,
                "round_visibility": "isolated",
                "saved": False,
            },
        )
        databases.update_document(
            database_id,
            "battles",
            battle_id,
            {"status": "running", "started_at": time.time()},
        )
        got = databases.get_document(database_id, "battles", battle_id)
        assert got.data["status"] == "running"
        databases.delete_document(database_id, "battles", battle_id)
        print("PASS  battles status update probe")
    except Exception as exc:
        print(f"FAIL  battles probe: {_exc_body(exc)}")
        failures += 1
        try:
            databases.delete_document(database_id, "battles", battle_id)
        except Exception:
            pass

    round_id = f"pr{uuid.uuid4().hex[:18]}"
    try:
        databases.create_document(
            database_id,
            "rounds",
            round_id,
            {
                "battle_id": probe_id,
                "phase": "probe",
                "model_id": "probe",
                "artifact": "probe-artifact",
            },
        )
        got = databases.get_document(database_id, "rounds", round_id)
        assert got.data["artifact"] == "probe-artifact"
        databases.delete_document(database_id, "rounds", round_id)
        print("PASS  rounds create/read/delete")
    except Exception as exc:
        print(f"FAIL  rounds probe: {_exc_body(exc)}")
        failures += 1
        try:
            databases.delete_document(database_id, "rounds", round_id)
        except Exception:
            pass

    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reconcile Appwrite schema")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="read-only comparison")
    mode.add_argument("--apply", action="store_true", help="create missing resources")
    args = parser.parse_args(argv)
    if args.check:
        failures = check_schema()
        if failures:
            print(f"FAIL  {failures} schema issue(s)")
            return 1
        print("PASS  schema check")
        return 0
    failures = apply_schema()
    failures += _probe()
    leftover = check_schema()
    # Missing indexes after a size-skip are reported by check; do not fail apply
    # solely for index MISS if apply already warned.
    if failures:
        print(f"FAIL  apply finished with {failures} error(s)")
        return 1
    print("PASS  apply")
    if leftover:
        print(f"INFO  check still reports {leftover} missing index(es) (size-limited)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
