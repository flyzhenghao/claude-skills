"""
Email notification stub (planned for v2.0).
"""

from __future__ import annotations

import logging
from typing import Any, List

from .base_notifier import BaseNotifier

logger = logging.getLogger(__name__)


class EmailNotifier(BaseNotifier):
    """
    Email notifier stub.
    """

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_addr: str,
        to_addrs: List[str]
    ) -> None:
        """
        Initialize email notifier.

        Args:
            smtp_host: SMTP server hostname.
            smtp_port: SMTP server port.
            username: SMTP username.
            password: SMTP password.
            from_addr: Sender email address.
            to_addrs: List of recipient email addresses.
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.to_addrs = to_addrs

    def validate_config(self) -> bool:
        """
        Validate email configuration.

        Returns:
            True if required fields are present, False otherwise.

        Raises:
            ValueError: If required configuration is missing.
        """
        if not self.smtp_host or self.smtp_port <= 0:
            logger.debug("Email config invalid: smtp_host missing or smtp_port <= 0")
            return False
        if not self.from_addr or not self.to_addrs:
            logger.debug("Email config invalid: from_addr or to_addrs missing")
            return False
        return True

    def send(self, title: str, message: str, **kwargs: Any) -> bool:
        """
        Send an email notification (stub).

        Args:
            title: Email subject line.
            message: Email body content.
            **kwargs: Provider-specific options (e.g., cc, bcc, attachments).

        Returns:
            True if the notification was accepted for delivery.

        Raises:
            NotImplementedError: Email notification not implemented yet.
        """
        # TODO(v2.0): Build MIME email with subject and message body.
        # TODO(v2.0): Connect to SMTP server and authenticate.
        # TODO(v2.0): Send email to recipients and handle failures.
        # TODO(v2.0): Support TLS/SSL and optional attachments.
        raise NotImplementedError("Email notification not implemented yet. Planned for v2.0")
