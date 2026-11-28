
# AI assistance used; implementation requires backend test validation.
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.auth import get_current_advisor
from app.dependencies.db import get_connection

router = APIRouter(
    prefix="/clients",
    tags=["Notes"],
    dependencies=[Depends(get_current_advisor)],
)


class NoteCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=5000)

    @field_validator("title", "content", mode="before")
    @classmethod
    def validate_text(cls, value):
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("This field cannot be empty.")
        return value


def verify_client_access(cur, client_id: int, advisor_id: int):
    cur.execute(
        """
        SELECT id
        FROM t_clients
        WHERE id = %(client_id)s
          AND advisor_id = %(advisor_id)s
        """,
        {
            "client_id": client_id,
            "advisor_id": advisor_id,
        },
    )

    if cur.fetchone() is None:
        raise HTTPException(
            status_code=404,
            detail="Client not found.",
        )


@router.get("/{client_id}/notes")
def list_client_notes(
    client_id: int,
    advisor: dict[str, int] = Depends(get_current_advisor),
):
    """Retrieve all notes belonging to a client."""

    with (
        get_connection(str(advisor["id"]), "Advisor") as conn,
        conn.cursor() as cur,
    ):
        verify_client_access(cur, client_id, advisor["id"])

        cur.execute(
            """
            SELECT id, title, content, client_id,
                   author_id, author_type::text AS author_type,
                   created_at, updated_at
            FROM t_notes
            WHERE client_id = %(client_id)s
            ORDER BY created_at DESC, id DESC
            """,
            {"client_id": client_id},
        )

        columns = [column.name for column in cur.description]
        rows = cur.fetchall()

    return [dict(zip(columns, row)) for row in rows]


@router.post("/{client_id}/notes", status_code=201)
def create_client_note(
    client_id: int,
    note: NoteCreate,
    advisor: dict[str, int] = Depends(get_current_advisor),
):
    """Create a note for the authenticated advisor's client."""

    with (
        get_connection(str(advisor["id"]), "Advisor") as conn,
        conn.cursor() as cur,
    ):
        verify_client_access(cur, client_id, advisor["id"])

        cur.execute(
            """
            INSERT INTO t_notes (
                title,
                content,
                client_id,
                author_id,
                author_type
            )
            VALUES (
                %(title)s,
                %(content)s,
                %(client_id)s,
                %(author_id)s,
                'Advisor'
            )
            RETURNING id, title, content, client_id,
                      author_id, author_type::text AS author_type,
                      created_at, updated_at
            """,
            {
                "title": note.title,
                "content": note.content,
                "client_id": client_id,
                "author_id": advisor["id"],
            },
        )

        columns = [column.name for column in cur.description]
        row = cur.fetchone()

    return dict(zip(columns, row))
