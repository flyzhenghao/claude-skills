"""
Abstract base class for notification providers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
import logging

logger = logging.getLogger(__name__)


class BaseNotifier(ABC):
    """
    Abstract base class for notification providers.

    Subclasses must implement configuration validation and message delivery.
    """

    @abstractmethod
    def send(self, title: str, message: str, **kwargs: Any) -> bool:
        """
        Send a notification.

        Args:
            title: Notification title.
            message: Notification body.
            **kwargs: Provider-specific options.

        Returns:
            True if the notification was accepted for delivery, False otherwise.

        Raises:
            NotImplementedError: If the notifier does not implement send().
            RuntimeError: If the provider fails to deliver the notification.
        """
        raise NotImplementedError("send() must be implemented by notifier subclasses")

    @abstractmethod
    def validate_config(self) -> bool:
        """
        Validate the notifier configuration.

        Returns:
            True if configuration is valid, False otherwise.

        Raises:
            ValueError: If required configuration is missing or invalid.
        """
        raise NotImplementedError("validate_config() must be implemented by notifier subclasses")
