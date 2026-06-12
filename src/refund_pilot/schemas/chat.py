from __future__ import annotations

from pydantic import UUID4, BaseModel, Field


class ConversationCreateRequest(BaseModel):
    customer_id: UUID4


class ConversationCreateResponse(BaseModel):
    conversation_id: str


class MessageRequest(BaseModel):
    order_id: UUID4
    message: str = Field(min_length=1, max_length=2000)


class MessageResponse(BaseModel):
    task_id: str


class StreamEvent(BaseModel):
    event: str
    data: dict[str, object]
