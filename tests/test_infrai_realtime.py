import httpx

from property_notify.infrai_realtime import InfraiRealtime


def test_create_channel_omits_optional_vendor() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/realtime/channel/create"
        assert request.headers["Idempotency-Key"] == "channel:property:cedar-house:user:tenant-4"
        assert request.read() == b'{"channel":"property:cedar-house:user:tenant-4","type":"private"}'
        return httpx.Response(200, json={"ok": True, "data": {}})

    realtime = InfraiRealtime(api_key="test-key", transport=httpx.MockTransport(respond))
    try:
        realtime.create_channel(
            "property:cedar-house:user:tenant-4",
            idempotency_key="channel:property:cedar-house:user:tenant-4",
        )
    finally:
        realtime.close()


def test_publish_sends_auth_and_idempotency_headers() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/v1/realtime/publish"
        assert request.headers["Authorization"] == "Bearer test-key"
        assert request.headers["Idempotency-Key"] == "maintenance:maint-11:urgent"
        return httpx.Response(200, json={"ok": True, "data": {"message_id": "msg-1"}})

    realtime = InfraiRealtime(api_key="test-key", transport=httpx.MockTransport(respond))
    try:
        result = realtime.publish(
            channel="property:cedar-house:user:tenant-4",
            event="maintenance.urgent",
            data={"request_id": "maint-11"},
            account_id="tenant-4",
            idempotency_key="maintenance:maint-11:urgent",
        )
    finally:
        realtime.close()

    assert result == {"message_id": "msg-1"}
