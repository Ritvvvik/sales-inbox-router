from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field, field_validator

AssigneeId = Literal["u_aarti", "u_rohit", "u_meera", "u_karan", "u_divya", "u_triage"]
Category = Literal["enterprise_rfp", "smb_enquiry", "marketing", "alliances", "finance", "triage"]
Priority = Literal["high", "medium", "low"]

ASSIGNEES = ["u_aarti", "u_rohit", "u_meera", "u_karan", "u_divya", "u_triage"]
CATEGORIES = ["enterprise_rfp", "smb_enquiry", "marketing", "alliances", "finance", "triage"]
PRIORITIES = ["high", "medium", "low"]

class Email(BaseModel):
    email_id: str
    thread_id: str
    message_index: int = 0
    from_name: str | None = None
    from_email: str | None = None
    to: str | None = None
    cc: list[str] = []
    subject: str = ""
    body: str = ""
    received_at: str
    attachments: list[str] = []
    is_reply: bool = False

class TaskCreate(BaseModel):
    candidate_id: str
    source_email_id: str
    thread_id: str
    title: str
    description: str | None = None
    assignee_id: AssigneeId
    category: Category
    priority: Priority
    due_date: str | None
    deal_value_inr: int | None
    company_name: str | None
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("candidate_id")
    @classmethod
    def normalize_candidate(cls, value: str) -> str:
        return value.strip().lower()

class TaskPatch(BaseModel):
    title: str | None = None
    description: str | None = None
    assignee_id: AssigneeId | None = None
    category: Category | None = None
    priority: Priority | None = None
    due_date: str | None = None
    deal_value_inr: int | None = None
    company_name: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)

class IngestRequest(BaseModel):
    candidate_id: str
    emails: list[Email]

    @field_validator("candidate_id")
    @classmethod
    def normalize_candidate(cls, value: str) -> str:
        return value.strip().lower()

class ChatRequest(BaseModel):
    candidate_id: str
    query: str

    @field_validator("candidate_id")
    @classmethod
    def normalize_candidate(cls, value: str) -> str:
        return value.strip().lower()
