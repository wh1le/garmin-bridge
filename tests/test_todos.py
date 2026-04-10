from unittest.mock import MagicMock

from src.todos import _stable_id, _handle_action, TODO_ACTIONS
from src import notifications


def test_stable_id_deterministic():
    assert _stable_id("Buy groceries") == _stable_id("Buy groceries")


def test_stable_id_different_for_different_text():
    assert _stable_id("Buy groceries") != _stable_id("Call dentist")


def test_stable_id_works_with_dict():
    assert _stable_id({"title": "Test"}) == _stable_id({"title": "Test"})


def test_todo_actions_has_done_remind_dismiss():
    codes = [code for code, _, _ in TODO_ACTIONS]

    assert notifications.ACTION_CUSTOM_1 in codes  # Done
    assert notifications.ACTION_CUSTOM_2 in codes  # Remind
    assert notifications.ACTION_DISMISS in codes    # Dismiss


def test_handle_action_done_removes_notification():
    protocol = MagicMock()
    protocol._pending_notifications = {
        12345: {"title": "Test", "body": ""},
    }

    _handle_action(protocol, 12345, notifications.ACTION_CUSTOM_1)
    assert 12345 not in protocol._pending_notifications


def test_handle_action_dismiss_removes_notification():
    protocol = MagicMock()
    protocol._pending_notifications = {
        12345: {"title": "Test", "body": ""},
    }

    _handle_action(protocol, 12345, notifications.ACTION_DISMISS)
    assert 12345 not in protocol._pending_notifications


def test_handle_action_remind_keeps_notification():
    protocol = MagicMock()
    protocol._pending_notifications = {
        12345: {"title": "Test", "body": ""},
    }
    protocol._transport = MagicMock()

    _handle_action(protocol, 12345, notifications.ACTION_CUSTOM_2)
    # Remind doesn't remove — it schedules a re-push
    assert 12345 in protocol._pending_notifications
