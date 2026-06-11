from __future__ import annotations

from app.config.runtime import load_alerting_settings
from app.notifications.providers import BrevoNotificationProvider, DryRunNotificationProvider, NotificationProvider, NotificationResult


def send_incident_notification(config: dict, payload: dict) -> NotificationResult:
    settings = load_alerting_settings(config)
    provider = _build_provider(settings.dry_run)
    return provider.send(settings, payload)


def _build_provider(dry_run: bool) -> NotificationProvider:
    if dry_run:
        return DryRunNotificationProvider()
    return BrevoNotificationProvider()
