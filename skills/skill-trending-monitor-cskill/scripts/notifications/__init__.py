"""
Notification system stubs for skill-trending-monitor-cskill (planned for v2.0).

These modules define notifier interfaces and placeholder implementations that
will be expanded in future releases.
"""

from .base_notifier import BaseNotifier
from .telegram_notifier import TelegramNotifier
from .email_notifier import EmailNotifier

__all__ = [
    "BaseNotifier",
    "TelegramNotifier",
    "EmailNotifier",
]
