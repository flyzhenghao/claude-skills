"""
Telegram notification stub (planned for v2.0).
"""

from __future__ import annotations

import logging
from typing import Any

from .base_notifier import BaseNotifier

logger = logging.getLogger(__name__)


class TelegramNotifier(BaseNotifier):
    """
    Telegram notifier stub.
    """

    def __init__(self, bot_token: str, chat_id: str) -> None:
        """
        Initialize Telegram notifier.

        Args:
            bot_token: Telegram bot token.
            chat_id: Target chat ID.
        """
        self.bot_token = bot_token
        self.chat_id = chat_id

    def validate_config(self) -> bool:
        """
        Validate Telegram configuration.

        Returns:
            True if required fields are present, False otherwise.

        Raises:
            ValueError: If required configuration is missing.
        """
        if not self.bot_token or not self.chat_id:
            logger.debug("Telegram config invalid: missing bot_token or chat_id")
            return False
        return True

    def send(self, title: str, message: str, **kwargs: Any) -> bool:
        """
        Send a Telegram notification (stub).

        Args:
            title: Notification title.
            message: Notification body.
            **kwargs: Provider-specific options (e.g., parse_mode).

        Returns:
            True if the notification was accepted for delivery.

        Raises:
            NotImplementedError: Telegram notification not implemented yet.
        """
        # TODO(v2.0): Build Telegram Bot API request payload (title + message).
        # TODO(v2.0): POST to Telegram sendMessage endpoint with chat_id.
        # TODO(v2.0): Handle timeouts, retries, and rate limiting.
        # TODO(v2.0): Parse response and return delivery status.
        raise NotImplementedError("Telegram notification not implemented yet. Planned for v2.0")
