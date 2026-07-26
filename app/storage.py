import json
import threading
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.config import Settings


class ObjectStore:
    """Small-object data store backed by three TOS buckets or an in-memory test backend."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._lock = threading.RLock()
        self._memory: dict[tuple[str, str], bytes] = {}
        self._memory_types: dict[tuple[str, str], str] = {}
        self._counters: dict[str, int] = defaultdict(int)
        self._client = None
        if settings.storage_backend == "tos":
            self._client = boto3.client(
                "s3",
                endpoint_url=settings.tos_s3_endpoint,
                aws_access_key_id=settings.tos_access_key_id,
                aws_secret_access_key=settings.tos_secret_access_key,
                region_name=settings.tos_region,
                config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
            )
            self._load_counters()

    def _key(self, key: str) -> str:
        clean = key.lstrip("/")
        prefix = self.settings.tos_prefix.strip("/")
        return f"{prefix}/{clean}" if prefix else clean

    def _raw_get(self, bucket: str, key: str) -> bytes | None:
        full_key = self._key(key)
        if self._client is None:
            return self._memory.get((bucket, full_key))
        try:
            return self._client.get_object(Bucket=self.settings.bucket_name(bucket), Key=full_key)["Body"].read()
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code in {"NoSuchKey", "404", "NotFound"}:
                return None
            raise

    def _raw_put(self, bucket: str, key: str, data: bytes, content_type: str) -> None:
        full_key = self._key(key)
        if self._client is None:
            self._memory[(bucket, full_key)] = data
            self._memory_types[(bucket, full_key)] = content_type
            return
        self._client.put_object(
            Bucket=self.settings.bucket_name(bucket),
            Key=full_key,
            Body=data,
            ContentType=content_type,
        )

    def _load_counters(self) -> None:
        raw = self._raw_get("a", "metrics/counters.json")
        if raw:
            self._counters.update(json.loads(raw.decode("utf-8")))

    def _persist_counters(self) -> None:
        payload = json.dumps(dict(self._counters), ensure_ascii=False).encode("utf-8")
        self._raw_put("a", "metrics/counters.json", payload, "application/json")

    def _bump(self, name: str, amount: int = 1) -> None:
        with self._lock:
            self._counters[name] += amount
            if self._client is not None:
                self._persist_counters()

    def put_json(self, bucket: str, key: str, value: Any) -> None:
        data = json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")
        with self._lock:
            self._raw_put(bucket, key, data, "application/json; charset=utf-8")
            self._bump("write_requests")

    def get_json(self, bucket: str, key: str) -> dict | list | None:
        with self._lock:
            raw = self._raw_get(bucket, key)
            self._bump("read_requests")
        return json.loads(raw.decode("utf-8")) if raw else None

    def atomic_update_json(self, bucket: str, key: str, mutator, default: Any = None) -> Any:
        """Best-effort read-modify-write guarded by the in-process lock.

        Object storage has no cross-process transaction, so this only serialises
        callers within a single process. Kept for API parity with MetadataStore
        (which is the production backend and is fully cross-process atomic)."""
        with self._lock:
            current = self.get_json(bucket, key)
            if current is None:
                current = default
            new_value = mutator(current)
            self.put_json(bucket, key, new_value)
            return new_value

    def claim_key(self, bucket: str, key: str, value: Any) -> bool:
        """Claim a unique index key (in-process guard). See MetadataStore.claim_key."""
        with self._lock:
            if self.get_json(bucket, key) is not None:
                return False
            self.put_json(bucket, key, value)
            return True

    def put_bytes(self, bucket: str, key: str, data: bytes, content_type: str) -> None:
        with self._lock:
            self._raw_put(bucket, key, data, content_type)
            self._bump("write_requests")
            self._bump("bytes_uploaded", len(data))

    def get_bytes(self, bucket: str, key: str) -> bytes | None:
        with self._lock:
            data = self._raw_get(bucket, key)
            self._bump("read_requests")
        return data

    def delete(self, bucket: str, key: str) -> None:
        full_key = self._key(key)
        with self._lock:
            if self._client is None:
                self._memory.pop((bucket, full_key), None)
                self._memory_types.pop((bucket, full_key), None)
            else:
                self._client.delete_object(Bucket=self.settings.bucket_name(bucket), Key=full_key)
            self._bump("delete_requests")

    def delete_prefix(self, bucket: str, prefix: str) -> int:
        full_prefix = self._key(prefix)
        deleted = 0
        with self._lock:
            if self._client is None:
                keys = [(alias, key) for alias, key in self._memory if alias == bucket and key.startswith(full_prefix)]
                for item in keys:
                    self._memory.pop(item, None)
                    self._memory_types.pop(item, None)
                    deleted += 1
            else:
                paginator = self._client.get_paginator("list_objects_v2")
                for page in paginator.paginate(Bucket=self.settings.bucket_name(bucket), Prefix=full_prefix):
                    objects = [{"Key": item["Key"]} for item in page.get("Contents", [])]
                    if objects:
                        self._client.delete_objects(
                            Bucket=self.settings.bucket_name(bucket), Delete={"Objects": objects, "Quiet": True}
                        )
                        deleted += len(objects)
            if deleted:
                self._bump("delete_requests", deleted)
        return deleted

    def list_json(self, bucket: str, prefix: str) -> list[dict]:
        full_prefix = self._key(prefix)
        values: list[dict] = []
        with self._lock:
            if self._client is None:
                keys = [key for alias, key in self._memory if alias == bucket and key.startswith(full_prefix)]
            else:
                keys = []
                paginator = self._client.get_paginator("list_objects_v2")
                for page in paginator.paginate(Bucket=self.settings.bucket_name(bucket), Prefix=full_prefix):
                    keys.extend(item["Key"] for item in page.get("Contents", []))
            for full_key in keys:
                if not full_key.endswith(".json"):
                    continue
                relative = (
                    full_key[len(self.settings.tos_prefix.strip("/")) + 1 :]
                    if self.settings.tos_prefix
                    else full_key
                )
                raw = self._raw_get(bucket, relative)
                if raw:
                    values.append(json.loads(raw.decode("utf-8")))
            self._bump("list_requests")
        return values

    def iter_json_entries(self, bucket: str) -> list[tuple[str, dict | list]]:
        """Return logical JSON keys with their values for a one-off metadata migration."""
        full_prefix = self._key("")
        if self._client is None:
            keys = [key for alias, key in self._memory if alias == bucket and key.startswith(full_prefix)]
        else:
            keys = []
            paginator = self._client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self.settings.bucket_name(bucket), Prefix=full_prefix):
                keys.extend(item["Key"] for item in page.get("Contents", []))
        entries: list[tuple[str, dict | list]] = []
        for full_key in keys:
            if not full_key.endswith(".json"):
                continue
            relative = full_key[len(full_prefix) :] if full_prefix else full_key
            raw = self._raw_get(bucket, relative)
            if raw:
                entries.append((relative, json.loads(raw.decode("utf-8"))))
        return entries

    def presigned_url(self, bucket: str, key: str, download_name: str | None = None) -> str:
        full_key = self._key(key)
        self._bump("presign_requests")
        if self._client is None:
            return f"memory://{bucket}/{full_key}"
        params = {"Bucket": self.settings.bucket_name(bucket), "Key": full_key}
        if download_name:
            params["ResponseContentDisposition"] = f'attachment; filename="{download_name}"'
        return self._client.generate_presigned_url(
            "get_object", Params=params, ExpiresIn=self.settings.tos_presign_seconds
        )

    def object_size(self, bucket: str, key: str) -> int:
        full_key = self._key(key)
        if self._client is None:
            return len(self._memory.get((bucket, full_key), b""))
        response = self._client.head_object(Bucket=self.settings.bucket_name(bucket), Key=full_key)
        return int(response.get("ContentLength", 0))

    def mark_download(self, size: int) -> None:
        self._bump("download_requests")
        self._bump("egress_bytes_estimated", max(0, size))

    def bucket_usage(self) -> dict[str, Any]:
        usage = {}
        for alias in ("a", "b", "c"):
            count = 0
            size = 0
            full_prefix = self._key("")
            if self._client is None:
                for (bucket, key), data in self._memory.items():
                    if bucket == alias and key.startswith(full_prefix):
                        count += 1
                        size += len(data)
            else:
                paginator = self._client.get_paginator("list_objects_v2")
                for page in paginator.paginate(Bucket=self.settings.bucket_name(alias), Prefix=full_prefix):
                    for item in page.get("Contents", []):
                        count += 1
                        size += int(item.get("Size", 0))
            usage[alias] = {"bucket": self.settings.bucket_name(alias), "objects": count, "bytes": size}
        requests = sum(value for key, value in self._counters.items() if key.endswith("requests"))
        total_bytes = sum(item["bytes"] for item in usage.values())
        egress = self._counters.get("egress_bytes_estimated", 0)
        return {
            "buckets": usage,
            "total_bytes": total_bytes,
            "requests": requests,
            "egress_bytes_estimated": egress,
            "counters": dict(self._counters),
            "warnings": {
                "storage": total_bytes >= self.settings.tos_warning_bytes,
                "requests": requests >= self.settings.tos_warning_requests,
                "egress": egress >= self.settings.tos_warning_egress_bytes,
            },
            "measured_at": datetime.now(timezone.utc).isoformat(),
            "note": "容量为实时对象汇总；请求和流出为本应用侧计数，控制台账单数据以火山引擎为准。",
        }
