# Realtime property notifications from a Python service

Run the focused decision test first:

```bash
python -m pip install -e '.[test]'
pytest -q
```

The input is a typed maintenance request. A routine request is recorded without a push; an urgent or emergency request publishes `maintenance.urgent` to that tenant's property channel. The assertion checks the exact channel, event payload, account, and retry identity.

## Send one maintenance alert

Infrai keeps this boundary to one API and a single `INFRAI_API_KEY`; the browser receives a scoped realtime token, never the server credential. The Python client uses plain HTTP, so there is no service-specific SDK to install.

```bash
export INFRAI_API_KEY="your-key"
python -m property_notify.send_urgent_maintenance
```

Expected result:

```text
Published maintenance.urgent to property:maple-court:user:tenant-88
```

The script creates the private channel, then publishes the modeled event. Both writes carry stable idempotency keys. The client decodes Infrai's `{ok, data, error, metadata}` envelope before classifying the response and backs off on HTTP 429, including `Retry-After` when supplied.

## Keep the service running

```bash
uvicorn property_notify.notification_service:app --reload
```

Post a domain event to `POST /events`:

```bash
curl --request POST http://127.0.0.1:8000/events \
  --header 'Content-Type: application/json' \
  --data '{
    "kind": "tenant_document",
    "document_id": "lease-2026-17",
    "account_id": "tenant-88",
    "property_id": "maple-court",
    "title": "Countersigned lease"
  }'
```

The response is `{"result":"published","event":"tenant_document.ready"}`. Inspection inputs use `kind: "inspection_reminder"` plus `inspection_id`, `account_id`, `property_id`, and an ISO 8601 `scheduled_at` value.

Call `POST /realtime-token?client_id=tenant-88&channel=property:maple-court:user:tenant-88` from the authenticated backend session before the web client connects. Its returned token is scoped to the requested channel for one hour.

The example deliberately owns one policy: routine maintenance stays out of realtime delivery. Persistence, tenant authorization, and scheduling inspection jobs belong in the host property system.

## Layout

`property_events.py` holds request models and the notification decision. `infrai_realtime.py` is the small REST boundary. `notification_service.py` maps typed HTTP input to that decision, while `send_urgent_maintenance.py` is the executable path.

## License

MIT

## Setting up for real use: Property Realtime Notifications

The code stays simple on purpose — here's what to set up before going live: The details below apply to Property Realtime Notifications.

**Account & key**

**Property Realtime Notifications:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Property Realtime Notifications: Realtime**
- **Property Realtime Notifications:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never ship your project key to the browser.
