import logging
import sys

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.dependencies.db import SessionLocal

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DEMO_CLIENTS = (
    {
        "name": "Alex Morgan (Demo)",
        "phone_number": "202-555-0101",
        "email": "alex.morgan.demo@example.com",
        "address": "100 Example Avenue, Demo City, ON",
        "age": 42,
        "occupation": "Teacher",
        "timeline": "Financial Needs Analysis",
    },
    {
        "name": "Jordan Lee (Demo)",
        "phone_number": "202-555-0102",
        "email": "jordan.lee.demo@example.com",
        "address": "200 Sample Street, Demo City, ON",
        "age": 36,
        "occupation": "Software designer",
        "timeline": "Investment Education",
    },
    {
        "name": "Sam Rivera (Demo)",
        "phone_number": "202-555-0103",
        "email": "sam.rivera.demo@example.com",
        "address": "300 Fiction Road, Demo City, ON",
        "age": 51,
        "occupation": "Small business owner",
        "timeline": "Financial Plan",
    },
    {
        "name": "Taylor Chen (Demo)",
        "phone_number": "202-555-0104",
        "email": "taylor.chen.demo@example.com",
        "address": "400 Example Lane, Demo City, ON",
        "age": 29,
        "occupation": "Healthcare administrator",
        "timeline": "Insurance Education",
    },
)

DEMO_TASKS = (
    ("alex.morgan.demo@example.com", "Review sample monthly budget", "TO_DO", 2),
    (
        "alex.morgan.demo@example.com",
        "Prepare sample planning summary",
        "IN_PROGRESS",
        4,
    ),
    (
        "jordan.lee.demo@example.com",
        "Compare sample education resources",
        "IN_REVIEW",
        3,
    ),
    ("jordan.lee.demo@example.com", "Send fictional meeting recap", "COMPLETED", -2),
    ("sam.rivera.demo@example.com", "Review sample business goals", "TO_DO", 6),
    (
        "sam.rivera.demo@example.com",
        "Prepare fictional cash-flow checklist",
        "IN_PROGRESS",
        1,
    ),
    (
        "taylor.chen.demo@example.com",
        "Review sample coverage checklist",
        "IN_REVIEW",
        5,
    ),
    ("taylor.chen.demo@example.com", "Send sample document checklist", "COMPLETED", -1),
)

DEMO_MEETINGS = (
    ("alex.morgan.demo@example.com", 2, 10),
    ("jordan.lee.demo@example.com", 4, 13),
    ("sam.rivera.demo@example.com", 7, 11),
    ("taylor.chen.demo@example.com", 10, 14),
)

DEMO_GOALS = (
    (
        "alex.morgan.demo@example.com",
        "Build an emergency-fund plan",
        "Short-term",
        "Savings",
    ),
    (
        "jordan.lee.demo@example.com",
        "Review long-term savings concepts",
        "Long-term",
        "Education",
    ),
    (
        "sam.rivera.demo@example.com",
        "Create a sample business continuity checklist",
        "Medium-term",
        "Business planning",
    ),
    (
        "taylor.chen.demo@example.com",
        "Understand sample insurance options",
        "Medium-term",
        "Insurance education",
    ),
)

DEMO_DOCUMENTS = (
    ("alex.morgan.demo@example.com", "Demo monthly budget worksheet", "Sent"),
    ("jordan.lee.demo@example.com", "Demo education resources", "Unsent"),
    ("sam.rivera.demo@example.com", "Demo business goals worksheet", "Completed"),
    ("taylor.chen.demo@example.com", "Demo coverage checklist", "Yet to Be Signed"),
)

DEMO_NOTES = (
    (
        "alex.morgan.demo@example.com",
        "Demo meeting goals",
        "Fictional demo note: discuss budgeting priorities and explain that all records in this database are sample data.",
    ),
    (
        "jordan.lee.demo@example.com",
        "Demo education follow-up",
        "Fictional demo note: share general educational resources and confirm the next sample meeting date.",
    ),
    (
        "sam.rivera.demo@example.com",
        "Demo planning discussion",
        "Fictional demo note: review the sample business-planning checklist; no real financial advice or client information is represented.",
    ),
    (
        "taylor.chen.demo@example.com",
        "Demo coverage questions",
        "Fictional demo note: collect questions for a general insurance-education discussion; this is not a real client record.",
    ),
)

DEMO_FOLLOW_UPS = (
    (
        "alex.morgan.demo@example.com",
        "Review the sample budget worksheet",
        "Financial Needs Analysis",
        3,
        "High",
    ),
    (
        "jordan.lee.demo@example.com",
        "Share general investment education resources",
        "Investment Education",
        5,
        "Medium",
    ),
    (
        "sam.rivera.demo@example.com",
        "Discuss the sample business-planning checklist",
        "Financial Plan",
        8,
        "Medium",
    ),
    (
        "taylor.chen.demo@example.com",
        "Send general insurance education material",
        "Insurance Education",
        6,
        "Low",
    ),
)

DEMO_TASK_BOARD_ITEMS = (
    (
        "alex.morgan.demo@example.com",
        "Review sample budget",
        "Discuss the fictional budget worksheet at the next demo meeting.",
        "Todo",
        3,
    ),
    (
        "jordan.lee.demo@example.com",
        "Share education resources",
        "Prepare general educational resources for the sample client.",
        "In-Progress",
        5,
    ),
    (
        "sam.rivera.demo@example.com",
        "Check sample planning notes",
        "Review the fictional business-planning notes.",
        "Resolved",
        -1,
    ),
    (
        "taylor.chen.demo@example.com",
        "Prepare coverage checklist",
        "Prepare a general education checklist for the demo meeting.",
        "Todo",
        4,
    ),
)


def _insert_demo_rows(db: Session, statement: str, rows: list[dict]) -> None:
    db.execute(text(statement), rows)


def seed_data(db: Session) -> None:
    advisor_ids = (
        db.execute(text("SELECT id FROM t_advisors ORDER BY id")).scalars().all()
    )

    if len(advisor_ids) != 1:
        logger.info(
            "Skipping demo data: expected exactly one advisor account, found %s.",
            len(advisor_ids),
        )
        return

    advisor_id = advisor_ids[0]
    _insert_demo_rows(
        db,
        """
        INSERT INTO t_clients (
            name, phone_number, email, address, age, occupation, timeline, advisor_id
        )
        VALUES (
            :name, :phone_number, :email, :address, :age, :occupation,
            CAST(:timeline AS timeline), :advisor_id
        )
        ON CONFLICT (email) DO NOTHING
        """,
        [{**client, "advisor_id": advisor_id} for client in DEMO_CLIENTS],
    )

    client_emails = [client["email"] for client in DEMO_CLIENTS]
    clients = db.execute(
        text("""
            SELECT id, email
            FROM t_clients
            WHERE advisor_id = :advisor_id AND email = ANY(:emails)
            """),
        {"advisor_id": advisor_id, "emails": client_emails},
    ).all()
    client_ids = {email: client_id for client_id, email in clients}

    if set(client_ids) != set(client_emails):
        raise RuntimeError(
            "Demo client email is already assigned to another advisor; "
            "no demo data was added."
        )

    _insert_demo_rows(
        db,
        """
        INSERT INTO t_tasks (advisor_id, client_id, task_title, status, due_date)
        SELECT
            :advisor_id, :client_id, CAST(:title AS varchar), :status,
            CURRENT_DATE + :due_in_days
        WHERE NOT EXISTS (
            SELECT 1 FROM t_tasks
            WHERE advisor_id = :advisor_id
              AND client_id = :client_id
              AND task_title = CAST(:title AS varchar)
        )
        """,
        [
            {
                "advisor_id": advisor_id,
                "client_id": client_ids[email],
                "title": title,
                "status": task_status,
                "due_in_days": due_in_days,
            }
            for email, title, task_status, due_in_days in DEMO_TASKS
        ],
    )

    _insert_demo_rows(
        db,
        """
        INSERT INTO t_meetings (advisor_id, client_id, meeting_date)
        SELECT
            :advisor_id, :client_id,
            date_trunc('hour', NOW()) + make_interval(days => :days, hours => :hours)
        WHERE NOT EXISTS (
            SELECT 1 FROM t_meetings
            WHERE advisor_id = :advisor_id
              AND client_id = :client_id
              AND meeting_date =
                  date_trunc('hour', NOW()) + make_interval(days => :days, hours => :hours)
        )
        """,
        [
            {
                "advisor_id": advisor_id,
                "client_id": client_ids[email],
                "days": days,
                "hours": hours,
            }
            for email, days, hours in DEMO_MEETINGS
        ],
    )

    _insert_demo_rows(
        db,
        """
        INSERT INTO t_consultations (
            client_id, advisor_id, meeting_time, duration, category, agenda,
            completion_status, location_or_platform
        )
        SELECT
            :client_id, :advisor_id,
            date_trunc('hour', NOW()) + make_interval(days => :days, hours => :hours),
            '30 minutes', 'Demo planning session',
            'Fictional sample agenda; no real client details.',
            'Scheduled', 'Online (demo)'
        WHERE NOT EXISTS (
            SELECT 1 FROM t_consultations
            WHERE advisor_id = :advisor_id
              AND client_id = :client_id
              AND category = 'Demo planning session'
              AND meeting_time =
                  date_trunc('hour', NOW()) + make_interval(days => :days, hours => :hours)
        )
        """,
        [
            {
                "advisor_id": advisor_id,
                "client_id": client_ids[email],
                "days": days,
                "hours": hours,
            }
            for email, days, hours in DEMO_MEETINGS
        ],
    )

    _insert_demo_rows(
        db,
        """
        INSERT INTO t_notes (content, title, client_id, author_id, author_type)
        SELECT :content, :title, :client_id, :advisor_id, 'Advisor'
        WHERE NOT EXISTS (
            SELECT 1 FROM t_notes
            WHERE client_id = :client_id
              AND author_id = :advisor_id
              AND title = :title
        )
        """,
        [
            {
                "client_id": client_ids[email],
                "advisor_id": advisor_id,
                "title": title,
                "content": content,
            }
            for email, title, content in DEMO_NOTES
        ],
    )

    _insert_demo_rows(
        db,
        """
        INSERT INTO t_goals (client_id, name, duration, type)
        SELECT :client_id, :name, CAST(:duration AS goal_duration), :type
        WHERE NOT EXISTS (
            SELECT 1 FROM t_goals
            WHERE client_id = :client_id AND name = :name
        )
        """,
        [
            {
                "client_id": client_ids[email],
                "name": name,
                "duration": duration,
                "type": goal_type,
            }
            for email, name, duration, goal_type in DEMO_GOALS
        ],
    )

    _insert_demo_rows(
        db,
        """
        INSERT INTO t_documents (client_id, name, status)
        SELECT :client_id, :name, CAST(:status AS document_status)
        WHERE NOT EXISTS (
            SELECT 1 FROM t_documents
            WHERE client_id = :client_id AND name = :name
        )
        """,
        [
            {
                "client_id": client_ids[email],
                "name": name,
                "status": document_status,
            }
            for email, name, document_status in DEMO_DOCUMENTS
        ],
    )

    _insert_demo_rows(
        db,
        """
        INSERT INTO follow_ups (
            advisor_id, client_id, reason, financial_planning_stage, due_date, priority
        )
        SELECT
            :advisor_id, :client_id, :reason,
            CAST(:stage AS timeline), CURRENT_DATE + :due_in_days,
            CAST(:priority AS follow_up_priority)
        WHERE NOT EXISTS (
            SELECT 1 FROM follow_ups
            WHERE advisor_id = :advisor_id
              AND client_id = :client_id
              AND reason = :reason
        )
        """,
        [
            {
                "advisor_id": advisor_id,
                "client_id": client_ids[email],
                "reason": reason,
                "stage": stage,
                "due_in_days": due_in_days,
                "priority": priority,
            }
            for email, reason, stage, due_in_days, priority in DEMO_FOLLOW_UPS
        ],
    )

    _insert_demo_rows(
        db,
        """
        INSERT INTO t_tasks_advisor (
            client_id, title, description, task_status, due_date
        )
        SELECT
            :client_id, :title, :description, CAST(:status AS task_status),
            NOW() + make_interval(days => :due_in_days)
        WHERE NOT EXISTS (
            SELECT 1 FROM t_tasks_advisor
            WHERE client_id = :client_id AND title = :title
        )
        """,
        [
            {
                "client_id": client_ids[email],
                "title": title,
                "description": description,
                "status": status,
                "due_in_days": due_in_days,
            }
            for email, title, description, status, due_in_days in DEMO_TASK_BOARD_ITEMS
        ],
    )

    db.commit()
    logger.info(
        "Seeded fictional demo data for advisor id %s (4 clients and related sample records).",
        advisor_id,
    )


def main() -> None:
    if settings.ENVIRONMENT == "production":
        logger.warning("Skipping seed_db: refusing to seed in production environment.")
        sys.exit(0)

    logger.info("Seeding database for environment '%s'...", settings.ENVIRONMENT)

    with SessionLocal() as db:
        seed_data(db)
    logger.info("Database seeding completed successfully.")


if __name__ == "__main__":
    main()
