from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Integer, MetaData, String, Table, Text

metadata = MetaData()


feature_flags_table = Table(
    "feature_flags",
    metadata,
    Column("name", String(127), primary_key=True),
    Column("enabled", Boolean, nullable=False),
    Column("rollout_percent", Integer, nullable=False),
    Column("description", Text),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)
