import json

from app import radar_sources


class _Response:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_collector_reports_access_rejection_instead_of_empty_success(monkeypatch) -> None:
    def fake_urlopen(*_args, **_kwargs):
        return _Response({"code": 0, "data": None, "message": "access restricted"})

    monkeypatch.setattr(radar_sources, "urlopen", fake_urlopen)

    jobs, report = radar_sources.GxrcPublicCollector().collect(pages=2)

    assert jobs == []
    assert report["successful_pages"] == 0
    assert len(report["failures"]) == 2
    assert "access restricted" in report["failures"][0]
