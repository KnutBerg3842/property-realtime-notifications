from .infrai_realtime import InfraiRealtime
from .property_events import MaintenanceRequest, decide_notification


def main() -> None:
    item = MaintenanceRequest(
        kind="maintenance_request",
        request_id="maint-1042",
        account_id="tenant-88",
        property_id="maple-court",
        summary="Water entering the electrical closet",
        priority="emergency",
    )
    notification = decide_notification(item)
    if notification is None:
        print("No realtime delivery required")
        return

    realtime = InfraiRealtime()
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
        print(f"Published {notification.event} to {notification.channel}")
    finally:
        realtime.close()


if __name__ == "__main__":
    main()

