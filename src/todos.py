"""Todo feature — push todos from config as notifications to watch.

Reads todos from config.yaml and sends them as notifications
after the watch subscribes (NOTIFICATION_SUBSCRIPTION enable=1).
Handles todo-specific actions: Done, Remind, Dismiss.
"""

import asyncio
import zlib

from src.config import config
from src.logger import log
from src import notifications
from src.protocol import MessageType

REMIND_DELAY_SECONDS = 30 * 60  # 30 minutes

TODO_ACTIONS = [
    (notifications.ACTION_CUSTOM_1, notifications.ICON_RIGHT,  "Done"),
    (notifications.ACTION_CUSTOM_2, notifications.ICON_BOTTOM, "Remind"),
    (notifications.ACTION_DISMISS,  notifications.ICON_LEFT,   "Dismiss"),
]


def register(protocol):
    """Register todo push and actions — triggers when watch subscribes."""
    protocol._notifications_pushed = False

    notifications.register(
        protocol,
        actions   = TODO_ACTIONS,
        on_action = _handle_action,
    )

    original_handler = protocol._handlers.get(MessageType.NOTIFICATION_SUBSCRIPTION)

    def on_subscription(_msg_type, payload):
        if original_handler:
            original_handler(_msg_type, payload)

        enable = payload[0] if len(payload) >= 1 else 0
        if enable == 1 and not protocol._notifications_pushed:
            protocol._notifications_pushed = True
            _push(protocol)

    protocol.on(MessageType.NOTIFICATION_SUBSCRIPTION, on_subscription)


def _push(protocol):
    """Push all todos from config as notifications."""
    todos = config.get("todos", [])
    if not todos:
        log.info("No todos configured")
        return

    log.info("Pushing %d todos as notifications", len(todos))

    for todo in todos:
        title = todo if isinstance(todo, str) else todo.get("title", "")
        body = "" if isinstance(todo, str) else todo.get("body", "")

        notifications.send(
            protocol,
            notification_id = _stable_id(todo),
            title           = title,
            body            = body,
            category        = notifications.CATEGORY_BUSINESS,
        )


def _handle_action(protocol, notification_id, action_id):
    """Handle todo actions from watch."""
    pending = getattr(protocol, "_pending_notifications", {})
    notification = pending.get(notification_id, {})
    title = notification.get("title", "unknown")

    if action_id == notifications.ACTION_CUSTOM_1:
        log.info("Todo done: %s", title)
        pending.pop(notification_id, None)

    elif action_id == notifications.ACTION_CUSTOM_2:
        log.info("Todo remind in %d min: %s", REMIND_DELAY_SECONDS // 60, title)
        asyncio.ensure_future(_remind_later(protocol, notification_id, notification))

    elif action_id == notifications.ACTION_DISMISS:
        log.info("Todo dismissed: %s", title)
        pending.pop(notification_id, None)

    else:
        log.info("Todo %d unknown action: %d", notification_id, action_id)


async def _remind_later(protocol, notification_id, notification):
    """Re-push a notification after REMIND_DELAY_SECONDS."""
    await asyncio.sleep(REMIND_DELAY_SECONDS)

    if not notification:
        return

    log.info("Reminding: %s", notification.get("title", ""))
    notifications.send(
        protocol,
        notification_id = notification_id,
        title           = notification["title"],
        body            = notification.get("body", ""),
        category        = notifications.CATEGORY_BUSINESS,
    )


def _stable_id(todo):
    """Generate a stable notification ID from todo text."""
    text = todo if isinstance(todo, str) else todo.get("title", "")
    return zlib.crc32(text.encode("utf-8")) & 0xFFFFFFFF
