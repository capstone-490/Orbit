from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.db.deps import get_db


class TestGetDb:
    @patch("app.db.deps.SessionLocal")
    def test_sets_empty_rls_context_without_header(self, mock_session_local):
        """Missing organization header defaults to no tenant."""
        db = MagicMock(spec=Session)
        mock_session_local.return_value = db

        generator = get_db()

        assert next(generator) is db

        db.execute.assert_called_once()

        args, kwargs = db.execute.call_args

        assert "set_config" in str(args[0])
        assert "app.current_org_id" in str(args[0])
        assert kwargs == {}

        with pytest.raises(StopIteration):
            next(generator)

        db.close.assert_called_once()

    @patch("app.db.deps.SessionLocal")
    def test_empty_organization_header_uses_default_context(self, mock_session_local):
        """An empty organization header behaves like a missing header."""
        db = MagicMock(spec=Session)
        mock_session_local.return_value = db

        generator = get_db(x_organization_id="")

        assert next(generator) is db

        args, kwargs = db.execute.call_args

        assert "app.current_org_id" in str(args[0])
        assert kwargs == {}

        generator.close()

        db.close.assert_called_once()

    @patch("app.db.deps.SessionLocal")
    def test_session_closed_when_consumer_raises(self, mock_session_local):
        """Session cleanup occurs when the consumer raises an exception."""
        db = MagicMock(spec=Session)
        mock_session_local.return_value = db

        generator = get_db()

        next(generator)

        with pytest.raises(RuntimeError, match="consumer failed"):
            generator.throw(RuntimeError("consumer failed"))

        db.close.assert_called_once()

    @patch("app.db.deps.SessionLocal")
    def test_session_closed_when_rls_setup_fails(self, mock_session_local):
        """Session is closed even if setting RLS context fails."""
        db = MagicMock(spec=Session)
        db.execute.side_effect = RuntimeError("database unavailable")
        mock_session_local.return_value = db

        generator = get_db(x_organization_id="org-123")

        with pytest.raises(RuntimeError, match="database unavailable"):
            next(generator)

        db.close.assert_called_once()

    @patch("app.db.deps.SessionLocal")
    def test_session_closed_exactly_once(self, mock_session_local):
        """Normal generator exhaustion must not close the session twice."""
        db = MagicMock(spec=Session)
        mock_session_local.return_value = db

        generator = get_db()

        next(generator)

        with pytest.raises(StopIteration):
            next(generator)

        db.close.assert_called_once()
