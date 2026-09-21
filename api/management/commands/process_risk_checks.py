import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from api.models import RiskCheckAttempt
from api.tasks import process_risk_check


class Command(BaseCommand):
    help = "Process queued plot risk checks from the database."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Process available work and exit.")
        parser.add_argument("--poll-seconds", type=float, default=None)

    def handle(self, *args, **options):
        poll_seconds = options["poll_seconds"]
        if poll_seconds is None:
            from django.conf import settings
            poll_seconds = settings.RISK_WORKER_POLL_SECONDS

        self.stdout.write(self.style.SUCCESS("Risk-check worker started."))
        while True:
            close_old_connections()
            attempt_ids = list(
                RiskCheckAttempt.objects.filter(status=RiskCheckAttempt.Status.QUEUED)
                .order_by("queued_at")
                .values_list("id", flat=True)[:10]
            )
            for attempt_id in attempt_ids:
                process_risk_check(attempt_id)
                self.stdout.write(f"Processed risk-check attempt {attempt_id}")
            if options["once"]:
                break
            if not attempt_ids:
                time.sleep(poll_seconds)
