import json
import logging
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import Plot, RiskCheckAttempt

logger = logging.getLogger(__name__)


def call_risk_registry(plot: Plot) -> dict[str, Any]:
    """Call the registry when configured, or use a deterministic local demo response."""
    if not settings.RISK_REGISTRY_URL:
        return {"status": "clear", "reference": f"local-demo-{plot.plot_code}"}

    payload = json.dumps({
        "plot_code": plot.plot_code,
        "administrative_sector": plot.administrative_sector,
        "latitude": str(plot.latitude) if plot.latitude is not None else None,
        "longitude": str(plot.longitude) if plot.longitude is not None else None,
    }).encode("utf-8")
    request = urllib.request.Request(
        settings.RISK_REGISTRY_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        result = json.loads(response.read().decode("utf-8"))
    return result


def process_risk_check(attempt_id: int) -> None:
    """Process one queued attempt. This function is called by the worker command."""
    attempt = RiskCheckAttempt.objects.select_related("plot").get(id=attempt_id)
    if attempt.status not in {RiskCheckAttempt.Status.QUEUED, RiskCheckAttempt.Status.FAILED}:
        return

    started = timezone.now()
    RiskCheckAttempt.objects.filter(id=attempt.id).update(
        status=RiskCheckAttempt.Status.RUNNING,
        started_at=started,
        error_message="",
    )
    Plot.objects.filter(id=attempt.plot_id).update(risk_status=Plot.RiskStatus.RUNNING)
    logger.info("risk_check_started plot=%s attempt=%s", attempt.plot.plot_code, attempt.id)

    try:
        result = call_risk_registry(attempt.plot)
        status = result.get("status", "clear")
        plot_status = Plot.RiskStatus.FLAGGED if status == "flagged" else Plot.RiskStatus.CLEAR
        with transaction.atomic():
            RiskCheckAttempt.objects.filter(id=attempt.id).update(
                status=RiskCheckAttempt.Status.SUCCEEDED,
                external_reference=str(result.get("reference", "")),
                finished_at=timezone.now(),
            )
            Plot.objects.filter(id=attempt.plot_id).update(
                risk_status=plot_status,
                risk_checked_at=timezone.now(),
            )
        logger.info("risk_check_succeeded plot=%s status=%s", attempt.plot.plot_code, plot_status)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        message = str(exc)[:500]
        RiskCheckAttempt.objects.filter(id=attempt.id).update(
            status=RiskCheckAttempt.Status.FAILED,
            error_message=message,
            finished_at=timezone.now(),
        )
        Plot.objects.filter(id=attempt.plot_id).update(risk_status=Plot.RiskStatus.FAILED)
        logger.warning("risk_check_failed plot=%s attempt=%s error=%s", attempt.plot.plot_code, attempt.id, message)
