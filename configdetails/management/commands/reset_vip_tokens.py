"""
Management command: reset_vip_tokens

Resets all VipTokenCounter rows back to (vip_from - 1) so the very
next VIP-token API call will issue vip_from as the first token of
the new day.

Usage
-----
    python manage.py reset_vip_tokens

Recommended cron (runs at midnight every day):
    0 0 * * * /path/to/venv/bin/python /path/to/manage.py reset_vip_tokens >> /var/log/callq/vip_reset.log 2>&1
"""

from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from configdetails.models import VipTokenCounter


class Command(BaseCommand):
    help = "Reset all VIP token counters to vip_from for the new day."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be reset without making any changes.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        today   = date.today()

        # Fetch every counter that either hasn't been reset today yet,
        # or has never been reset at all.
        pending_qs = VipTokenCounter.objects.select_for_update().exclude(
            last_reset_date=today
        )

        count = pending_qs.count()

        if count == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"[{today}] All VIP token counters already reset for today. Nothing to do."
                )
            )
            return

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"[DRY-RUN] {count} VIP token counter(s) would be reset to their vip_from value."
                )
            )
            for vtc in pending_qs:
                self.stdout.write(
                    f"  • Counter '{vtc.counter.counter_name}' / "
                    f"Dispenser '{vtc.dispenser.serial_number}' — "
                    f"current: {vtc.current_token} → reset to {vtc.vip_from - 1} "
                    f"(first token will be {vtc.vip_from})"
                )
            return

        # ── Perform the reset inside a single transaction ────────────────────
        with transaction.atomic():
            reset_count = 0
            for vtc in pending_qs:
                vtc.current_token   = vtc.vip_from - 1
                vtc.last_reset_date = today
                vtc.save(update_fields=["current_token", "last_reset_date", "updated_at"])
                reset_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"[{today}] Successfully reset {reset_count} VIP token counter(s) to their vip_from values."
            )
        )
