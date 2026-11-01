from enum import Enum
from datetime import datetime
from pydantic import BaseModel

from app.services.sla_cal import (
    UrgencyState
)

class TaskStatus(Enum):
    Todo = "Todo"
    InProgress = "In-Progress"
    Resolved = "Resolved"


class TaskCreate(BaseModel):
    title: str | None = None
    description: str | None = None
    client_id: int
    task_status: TaskStatus = TaskStatus.Todo
    due_date: datetime
    last_contact_date: datetime | None = None

class TaskResponse(BaseModel):

    id: int
    title: str | None
    description: str | None
    client_id: int
    task_status: TaskStatus        
    due_date: datetime
    last_contact_date: datetime | None
    urgency_state: UrgencyState
    urgency_color: str
