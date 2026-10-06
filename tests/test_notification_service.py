from fastapi.testclient import TestClient

from property_notify.infrai_realtime import InfraiRealtime
from property_notify.notification_service import app, realtime_client


class RecordingRealtime:
    def __init__(self) -> None:
        self.created: list[tuple[str, str]] = []
        self.published: list[dict[str, object]] = []

    def create_channel(self, channel: str, *, idempotency_key: str) -> dict[str, object]:
        self.created.append((channel, idempotency_key))
        return {}

    def publish(self, **payload: object) -> dict[str, object]:
        self.published.append(payload)
        return {}


def test_only_urgent_maintenance_is_published() -> None:
    recorder = RecordingRealtime()
    app.dependency_overrides[realtime_client] = lambda: recorder
    client = TestClient(app)

    routine = client.post(
        "/events",
        json={
            "kind": "maintenance_request",
            "request_id": "maint-10",
            "account_id": "tenant-4",
            "property_id": "cedar-house",
            "summary": "Bedroom door sticks",
            "priority": "routine",
        },
    )
    urgent = client.post(
        "/events",
        json={
            "kind": "maintenance_request",
            "request_id": "maint-11",
            "account_id": "tenant-4",
            "property_id": "cedar-house",
            "summary": "No heat during freezing weather",
            "priority": "urgent",
        },
    )

    assert routine.json() == {"result": "recorded", "delivery": "not_required"}
    assert urgent.json() == {"result": "published", "event": "maintenance.urgent"}
    assert recorder.created == [
        ("property:cedar-house:user:tenant-4", "channel:property:cedar-house:user:tenant-4")
    ]
    assert recorder.published == [
        {
            "channel": "property:cedar-house:user:tenant-4",
            "event": "maintenance.urgent",
            "data": {
                "request_id": "maint-11",
                "summary": "No heat during freezing weather",
                "priority": "urgent",
            },
            "account_id": "tenant-4",
            "idempotency_key": "maintenance:maint-11:urgent",
        }
    ]
    app.dependency_overrides.clear()

