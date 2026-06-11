from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from urllib import error, request

from app.config.runtime import AlertingSettings


@dataclass
class NotificationResult:
    success: bool
    provider: str
    mode: str
    attempts: int
    status_code: int | None
    detail: str

    def to_dict(self) -> dict:
        return asdict(self)


class NotificationProvider:
    def send(self, settings: AlertingSettings, payload: dict) -> NotificationResult:
        raise NotImplementedError


class DryRunNotificationProvider(NotificationProvider):
    def send(self, settings: AlertingSettings, payload: dict) -> NotificationResult:
        _ = settings, payload
        return NotificationResult(True, "brevo", "dry-run", 0, None, "dry-run notification recorded without external delivery")


class BrevoNotificationProvider(NotificationProvider):
    ENDPOINT = "https://api.brevo.com/v3/smtp/email"

    def send(self, settings: AlertingSettings, payload: dict) -> NotificationResult:
        body = json.dumps(
            {
                "sender": {"email": settings.from_email},
                "to": [{"email": settings.to_email}],
                "subject": payload["subject"],
                "textContent": payload["body"],
            }
        ).encode("utf-8")
        attempts = 0
        max_attempts = settings.max_retries + 1
        while attempts < max_attempts:
            attempts += 1
            req = request.Request(
                self.ENDPOINT,
                data=body,
                headers={
                    "accept": "application/json",
                    "api-key": settings.api_key or "",
                    "content-type": "application/json",
                },
                method="POST",
            )
            try:
                with request.urlopen(req, timeout=settings.timeout_seconds) as response:
                    status_code = getattr(response, "status", None)
                    if status_code is not None and 200 <= status_code < 300:
                        return NotificationResult(True, "brevo", "live", attempts, status_code, "notification sent")
                    return NotificationResult(False, "brevo", "live", attempts, status_code, f"unexpected_http_status:{status_code}")
            except error.HTTPError as exc:
                if attempts >= max_attempts:
                    return NotificationResult(False, "brevo", "live", attempts, exc.code, f"http_error:{exc.code}")
            except error.URLError:
                if attempts >= max_attempts:
                    return NotificationResult(False, "brevo", "live", attempts, None, "transport_error")
        return NotificationResult(False, "brevo", "live", attempts, None, "retry_exhausted")
