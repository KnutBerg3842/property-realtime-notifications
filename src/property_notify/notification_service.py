from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status

from .infrai_realtime import InfraiError, InfraiRealtime
from .property_events import PropertyEvent, decide_notification

_realtime: InfraiRealtime | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    global _realtime
    _realtime = InfraiRealtime()
    yield
    _realtime.close()
    _realtime = None


app = FastAPI(title="Property notification service", lifespan=lifespan)


def realtime_client() -> InfraiRealtime:
    if _realtime is None:
        raise RuntimeError("service has not started")
    return _realtime


@app.post("/events", status_code=status.HTTP_202_ACCEPTED)
def accept_event(
    item: PropertyEvent,
    realtime: Annotated[InfraiRealtime, Depends(realtime_client)],
) -> dict[str, str]:
    notification = decide_notification(item)
    if notification is None:
        return {"result": "recorded", "delivery": "not_required"}

    try:
        realtime.create_channel(
            notification.channel,
            idempotency_key=f"channel:{notification.channel}",
        )
        realtime.publish(
            channel=notification.channel,
            event=notification.event,
            data=notification.data,
            account_id=notification.account_id,
            idempotency_key=notification.delivery_id,
        )
    except InfraiError as exc:
        client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=client_status,
            detail={"code": exc.code, "error": exc.details},
        ) from exc

    return {"result": "published", "event": notification.event}


@app.post("/realtime-token")
def realtime_token(
    client_id: str,
    channel: str,
    realtime: Annotated[InfraiRealtime, Depends(realtime_client)],
) -> dict[str, object]:
    try:
        return realtime.issue_token(client_id, [channel])
    except InfraiError as exc:
        client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=client_status,
            detail={"code": exc.code, "error": exc.details},
        ) from exc

