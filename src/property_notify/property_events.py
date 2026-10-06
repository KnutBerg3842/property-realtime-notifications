from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class MaintenanceRequest(BaseModel):
    kind: Literal["maintenance_request"]
    request_id: str
    account_id: str
    property_id: str
    summary: str
    priority: Literal["routine", "urgent", "emergency"]


class TenantDocument(BaseModel):
    kind: Literal["tenant_document"]
    document_id: str
    account_id: str
    property_id: str
    title: str


class InspectionReminder(BaseModel):
    kind: Literal["inspection_reminder"]
    inspection_id: str
    account_id: str
    property_id: str
    scheduled_at: datetime


PropertyEvent = Annotated[
    MaintenanceRequest | TenantDocument | InspectionReminder,
    Field(discriminator="kind"),
]


class Notification(BaseModel):
    channel: str
    event: str
    data: dict[str, str]
    account_id: str
    delivery_id: str


def decide_notification(item: PropertyEvent) -> Notification | None:
    channel = f"property:{item.property_id}:user:{item.account_id}"

    if isinstance(item, MaintenanceRequest):
        if item.priority == "routine":
            return None
        return Notification(
            channel=channel,
            event="maintenance.urgent",
            data={
                "request_id": item.request_id,
                "summary": item.summary,
                "priority": item.priority,
            },
            account_id=item.account_id,
            delivery_id=f"maintenance:{item.request_id}:{item.priority}",
        )

    if isinstance(item, TenantDocument):
        return Notification(
            channel=channel,
            event="tenant_document.ready",
            data={"document_id": item.document_id, "title": item.title},
            account_id=item.account_id,
            delivery_id=f"document:{item.document_id}:ready",
        )

    return Notification(
        channel=channel,
        event="inspection.reminder",
        data={
            "inspection_id": item.inspection_id,
            "scheduled_at": item.scheduled_at.isoformat(),
        },
        account_id=item.account_id,
        delivery_id=f"inspection:{item.inspection_id}:{item.scheduled_at.isoformat()}",
    )

