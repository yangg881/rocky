import asyncio
from datetime import datetime, timedelta, timezone

from app.radar import JobRadarStore


def test_quality_check_keeps_valid_roles_and_rejects_only_bad_records(tmp_path) -> None:
    store = JobRadarStore(tmp_path / "radar.sqlite3")
    published = datetime.now(timezone.utc).isoformat()

    valid = store.normalize_job({
        "id": "warehouse-role",
        "title": "Warehouse operator",
        "company": "Example Logistics",
        "description": "Pick, pack and inventory work.",
        "published_at": published,
    })
    generic = store.normalize_job({
        "id": "generic-role",
        "title": "\u5c97\u4f4d",
        "company": "Example Logistics",
        "published_at": published,
    })
    promotional = store.normalize_job({
        "id": "promotional-role",
        "title": "Warehouse operator",
        "company": "Example Logistics",
        "description": "\u626b\u7801\u8fdb\u7fa4\u4e86\u89e3\u66f4\u591a\u4fe1\u606f",
        "published_at": published,
    })

    assert valid is not None
    assert generic is None
    assert promotional is None


def test_only_new_uses_published_time_and_summary_counts_all_new_jobs(tmp_path) -> None:
    store = JobRadarStore(tmp_path / "radar.sqlite3")
    store.initialize()
    now = datetime.now(timezone.utc)
    store.import_jobs([
        {
            "id": "fresh-job",
            "title": "Fresh role",
            "company": "Example Co",
            "published_at": now.isoformat(),
        },
        {
            "id": "old-job",
            "title": "Old role",
            "company": "Example Co",
            "published_at": (now - timedelta(days=2)).isoformat(),
        },
    ])

    result = asyncio.run(store.recommend("user-1", "role", only_new=True))

    assert [job["id"] for job in result.jobs] == ["fresh-job"]
    assert store.summary("user-1")["new_jobs"] == 1


def test_recommendation_batch_keeps_true_match_count_before_cap(tmp_path) -> None:
    store = JobRadarStore(tmp_path / "radar.sqlite3")
    store.initialize()
    store.import_jobs(
        [
            {"id": "job-1", "title": "运营主管", "source_url": "https://example.com/job-1", "published_at": datetime.now(timezone.utc).isoformat()},
            {"id": "job-2", "title": "运营经理", "source_url": "https://example.com/job-2", "published_at": datetime.now(timezone.utc).isoformat()},
            {"id": "job-3", "title": "内容运营", "source_url": "https://example.com/job-3", "published_at": datetime.now(timezone.utc).isoformat()},
        ]
    )

    result = asyncio.run(store.recommend("user-1", "运营", query="运营", max_results=2))

    assert result.matched_total == 3
    assert result.is_limited is True
    assert len(result.jobs) == 2


def test_recommendation_source_filter_uses_source_host(tmp_path) -> None:
    store = JobRadarStore(tmp_path / "radar.sqlite3")
    store.initialize()
    published = datetime.now(timezone.utc).isoformat()
    store.import_jobs([
        {
            "id": "gxrc-1",
            "title": "广西岗位",
            "source_url": "https://www.gxrc.com/jobDetail/1",
            "published_at": published,
        },
        {
            "id": "51job-1",
            "title": "前程岗位",
            "source_url": "https://jobs.51job.com/job/1",
            "published_at": published,
        },
    ])

    result = asyncio.run(store.recommend("user-1", "岗位", source="gxrc"))

    assert [job["id"] for job in result.jobs] == ["gxrc-1"]


def test_completed_generation_sync_marks_radar_job(tmp_path) -> None:
    store = JobRadarStore(tmp_path / "radar.sqlite3")
    store.initialize()
    store.import_jobs([
        {"id": "job-1", "title": "运营经理", "source_url": "https://example.com/job-1", "published_at": datetime.now(timezone.utc).isoformat()},
    ])
    store.sync_completed_adaptations("user-1", [
        {"id": "generation-1", "radar_job_id": "job-1", "status": "completed", "updated_at": datetime.now(timezone.utc).isoformat()},
        {"id": "generation-2", "radar_job_id": "job-1", "status": "failed"},
    ])

    result = asyncio.run(store.recommend("user-1", "运营"))

    assert result.jobs[0]["adapted"] is True
    assert result.jobs[0]["adapted_generation_id"] == "generation-1"


def test_cleanup_inactive_jobs(tmp_path) -> None:
    from datetime import timedelta
    store = JobRadarStore(tmp_path / "radar.sqlite3")
    store.initialize()

    now = datetime.now(timezone.utc)
    old_published = (now - timedelta(days=35)).isoformat()
    stale_captured = (now - timedelta(days=20)).isoformat()
    recent = now.isoformat()

    store.import_jobs([
        {"id": "job-valid", "title": "有效岗位", "source_url": "https://example.com/1", "published_at": recent, "captured_at": recent},
        {"id": "job-old-pub", "title": "超期岗位", "source_url": "https://example.com/2", "published_at": recent, "captured_at": recent},
        {"id": "job-stale-cap", "title": "未刷新岗位", "source_url": "https://example.com/3", "published_at": recent, "captured_at": stale_captured},
        {"id": "job-unavail", "title": "已下架岗位", "source_url": "https://example.com/4", "published_at": recent, "captured_at": recent, "source_detail_status": "unavailable"},
    ])

    # Manually age job-old-pub's published_at date to 35 days ago
    with store.connection() as conn:
        conn.execute("UPDATE jobs SET published_at = ? WHERE id = 'job-old-pub'", (old_published,))

    # Test dry run
    dry_res = store.cleanup_inactive_jobs(max_published_days=30, max_stale_days=14, dry_run=True)
    assert dry_res["total_deactivated"] == 3
    assert store.job_count() == 4

    # Test actual cleanup
    clean_res = store.cleanup_inactive_jobs(max_published_days=30, max_stale_days=14, dry_run=False)
    assert clean_res["total_deactivated"] == 3
    assert store.job_count() == 1
    assert store.get_job("job-valid") is not None
    assert store.get_job("job-old-pub") is None


def test_update_job_details_deactivates_unavailable(tmp_path) -> None:
    store = JobRadarStore(tmp_path / "radar.sqlite3")
    store.initialize()

    store.import_jobs([
        {"id": "job-1", "title": "测试岗位", "source_url": "https://example.com/1", "published_at": datetime.now(timezone.utc).isoformat()},
    ])

    assert store.get_job("job-1") is not None

    # Update job details to unavailable
    store.update_job_details("job-1", {"source_detail_status": "unavailable"})
    assert store.get_job("job-1") is None
    assert store.job_count() == 0


def test_cleanup_guard_aborts_large_batch_without_writes(tmp_path) -> None:
    store = JobRadarStore(tmp_path / "radar.sqlite3")
    store.initialize()
    recent = datetime.now(timezone.utc).isoformat()
    store.import_jobs([
        {
            "id": f"job-{index}",
            "title": "娴嬭瘯宀椾綅",
            "source_url": f"https://example.com/{index}",
            "published_at": recent,
            "captured_at": recent,
            "source_detail_status": "unavailable",
        }
        for index in range(101)
    ])

    result = store.cleanup_inactive_jobs(dry_run=False)

    assert result["guard_blocked"] == 1
    assert result["proposed_deactivated"] == 101
    assert result["total_deactivated"] == 0
    assert store.job_count() == 101
