# Substantial AI assistance used; verified with backend unit tests.
"""Ranking rules for the advisor dashboard's priority actions.

The criteria are documented in docs/priority-actions.md. Keep the two in sync.
"""

from datetime import date

ACTIVE_STATUSES = ("Pending", "In Progress")

# A follow-up is "due soon" when it is due within this many days (0 = today).
DUE_SOON_DAYS = 2
# High-priority follow-ups are surfaced up to this many days ahead.
HIGH_PRIORITY_WINDOW_DAYS = 7

URGENCY_ORDER = {"overdue": 0, "due_soon": 1, "high_priority": 2}
PRIORITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}


def classify_urgency(follow_up: dict, today: date) -> str | None:
    """Return the urgency category of a follow-up, or None if it is not urgent."""
    if follow_up["status"] not in ACTIVE_STATUSES:
        return None

    days_until_due = (follow_up["due_date"] - today).days
    if days_until_due < 0:
        return "overdue"
    if days_until_due <= DUE_SOON_DAYS:
        return "due_soon"
    if (
        follow_up["priority"] == "High"
        and days_until_due <= HIGH_PRIORITY_WINDOW_DAYS
    ):
        return "high_priority"
    return None


def describe_urgency(urgency: str, days_until_due: int) -> str:
    """Short, human-readable explanation shown next to each item."""
    if urgency == "overdue":
        days = -days_until_due
        return f"Overdue by {days} day{'s' if days != 1 else ''}"
    if days_until_due == 0:
        return "Due today"
    if days_until_due == 1:
        return "Due tomorrow"
    if urgency == "due_soon":
        return f"Due in {days_until_due} days"
    return f"High priority, due in {days_until_due} days"


def rank_priority_actions(follow_ups: list[dict], today: date) -> list[dict]:
    """Filter follow-ups down to urgent ones and sort them most urgent first.

    Order: urgency category (overdue, due soon, high priority), then the
    follow-up's priority (High, Medium, Low), then earliest due date, then id.
    """
    actions = []
    for follow_up in follow_ups:
        urgency = classify_urgency(follow_up, today)
        if urgency is None:
            continue

        days_until_due = (follow_up["due_date"] - today).days
        actions.append(
            {
                "follow_up_id": follow_up["id"],
                "client_id": follow_up["client_id"],
                "client_name": follow_up.get("client_name"),
                "reason": follow_up["reason"],
                "financial_planning_stage": follow_up.get("financial_planning_stage"),
                "due_date": follow_up["due_date"],
                "priority": follow_up["priority"],
                "status": follow_up["status"],
                "urgency": urgency,
                "days_until_due": days_until_due,
                "urgency_reason": describe_urgency(urgency, days_until_due),
            }
        )

    actions.sort(
        key=lambda action: (
            URGENCY_ORDER[action["urgency"]],
            PRIORITY_ORDER.get(action["priority"], len(PRIORITY_ORDER)),
            action["due_date"],
            action["follow_up_id"],
        )
    )
    return actions