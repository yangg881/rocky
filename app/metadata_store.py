"""PostgreSQL-backed metadata facade; TOS remains the binary artifact backend."""

from __future__ import annotations

from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from app.storage import ObjectStore


class MetadataStore:
    """Move business records into PostgreSQL without breaking stable API key paths."""

    def __init__(self, files: ObjectStore, database_url: str):
        self.files = files
        self.database_url = database_url

    def initialize(self) -> None:
        with psycopg.connect(self.database_url) as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS metadata_records (
                    bucket TEXT NOT NULL,
                    record_key TEXT NOT NULL,
                    value JSONB NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (bucket, record_key)
                );
                CREATE INDEX IF NOT EXISTS idx_metadata_records_prefix
                    ON metadata_records (bucket, record_key text_pattern_ops);
                """
            )

    def put_json(self, bucket: str, key: str, value: Any) -> None:
        if bucket != "a":
            self.files.put_json(bucket, key, value)
            return
        with psycopg.connect(self.database_url) as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO metadata_records (bucket, record_key, value)
                VALUES (%s, %s, %s)
                ON CONFLICT (bucket, record_key)
                DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
                """,
                (bucket, key, Jsonb(value)),
            )

    def get_json(self, bucket: str, key: str) -> dict | list | None:
        if bucket != "a":
            return self.files.get_json(bucket, key)
        with psycopg.connect(self.database_url) as connection, connection.cursor() as cursor:
            cursor.execute("SELECT value FROM metadata_records WHERE bucket = %s AND record_key = %s", (bucket, key))
            row = cursor.fetchone()
        return row[0] if row else None

    def atomic_update_json(self, bucket: str, key: str, mutator, default: Any = None) -> Any:
        """Read-modify-write a record atomically across processes.

        For the PostgreSQL-backed bucket ``"a"`` the row is locked with
        ``SELECT ... FOR UPDATE`` for the whole transaction, so concurrent callers
        (web process + task workers) serialise instead of racing (fixes credit
        double-spend / register races). ``mutator`` receives the current value
        (or ``default`` when the row is absent) and returns the new value; it may
        raise to abort, in which case the transaction rolls back untouched.
        """
        if bucket != "a":
            current = self.files.get_json(bucket, key)
            if current is None:
                current = default
            new_value = mutator(current)
            self.files.put_json(bucket, key, new_value)
            return new_value
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                if default is not None:
                    cursor.execute(
                        """
                        INSERT INTO metadata_records (bucket, record_key, value)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (bucket, record_key) DO NOTHING
                        """,
                        (bucket, key, Jsonb(default)),
                    )
                cursor.execute(
                    "SELECT value FROM metadata_records WHERE bucket = %s AND record_key = %s FOR UPDATE",
                    (bucket, key),
                )
                row = cursor.fetchone()
                current = row[0] if row else default
                new_value = mutator(current)
                cursor.execute(
                    """
                    INSERT INTO metadata_records (bucket, record_key, value)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (bucket, record_key)
                    DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
                    """,
                    (bucket, key, Jsonb(new_value)),
                )
        return new_value

    def claim_key(self, bucket: str, key: str, value: Any) -> bool:
        """Atomically claim a unique index key. Returns True if newly claimed,
        False if it already existed. Used for register uniqueness (P0-2)."""
        if bucket != "a":
            existing = self.files.get_json(bucket, key)
            if existing is not None:
                return False
            self.files.put_json(bucket, key, value)
            return True
        with psycopg.connect(self.database_url) as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO metadata_records (bucket, record_key, value)
                VALUES (%s, %s, %s)
                ON CONFLICT (bucket, record_key) DO NOTHING
                """,
                (bucket, key, Jsonb(value)),
            )
            return cursor.rowcount == 1

    def list_json(self, bucket: str, prefix: str) -> list[dict]:
        if bucket != "a":
            return self.files.list_json(bucket, prefix)
        with psycopg.connect(self.database_url) as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT value FROM metadata_records WHERE bucket = %s AND record_key LIKE %s ORDER BY record_key",
                (bucket, f"{prefix}%"),
            )
            return [row[0] for row in cursor.fetchall()]

    def delete(self, bucket: str, key: str) -> None:
        if bucket != "a":
            self.files.delete(bucket, key)
            return
        with psycopg.connect(self.database_url) as connection, connection.cursor() as cursor:
            cursor.execute("DELETE FROM metadata_records WHERE bucket = %s AND record_key = %s", (bucket, key))

    def delete_prefix(self, bucket: str, prefix: str) -> int:
        if bucket != "a":
            return self.files.delete_prefix(bucket, prefix)
        with psycopg.connect(self.database_url) as connection, connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM metadata_records WHERE bucket = %s AND record_key LIKE %s",
                (bucket, f"{prefix}%"),
            )
            return cursor.rowcount

    def put_bytes(self, bucket: str, key: str, data: bytes, content_type: str) -> None:
        self.files.put_bytes(bucket, key, data, content_type)

    def get_bytes(self, bucket: str, key: str) -> bytes | None:
        return self.files.get_bytes(bucket, key)

    def presigned_url(self, bucket: str, key: str, download_name: str | None = None) -> str:
        return self.files.presigned_url(bucket, key, download_name)

    def object_size(self, bucket: str, key: str) -> int:
        return self.files.object_size(bucket, key)

    def mark_download(self, size: int) -> None:
        self.files.mark_download(size)

    def bucket_usage(self) -> dict[str, Any]:
        return self.files.bucket_usage()
