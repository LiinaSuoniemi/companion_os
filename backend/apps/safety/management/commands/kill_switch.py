"""
kill_switch management command.

Decouples the maintenance mode kill switch from admin login.

Why this exists
---------------
The kill switch lives in SystemConfig (single DB row, pk=1). Flipping it
normally requires logging into /admin/ and editing the row. If admin login
is broken (TOTP locked out, axes throttled, password forgotten), the
operator cannot stop the service from inside the app.

This command runs anywhere with database access — Railway shell, local
Docker exec, a CI job, an emergency runbook. No admin login required.

Usage
-----
Railway production:
    railway run python manage.py kill_switch status
    railway run python manage.py kill_switch on
    railway run python manage.py kill_switch off

Local Docker:
    docker compose exec web python manage.py kill_switch status

With custom message (only relevant with 'on'):
    railway run python manage.py kill_switch on --message "Down for safety check, back in 30 min"

Scripted / non-interactive (skip the YES confirmation):
    railway run python manage.py kill_switch on --yes

Design decisions
----------------
1. 'on' requires typing 'YES' (not just y/n) to confirm.
   Friction is intentional — kill switch ON halts all traffic.
2. 'off' needs no confirmation. Restoring access is always cheap.
3. 'status' never modifies state. Safe to run anytime.
4. Output goes to stdout, plain text. Readable even if logging breaks.
5. Toggles are logged at WARNING level so they surface in Railway logs.
6. DB errors raise CommandError (exit code 1). The middleware itself
   fails open, so a DB outage does NOT block normal traffic — but this
   command needs DB to do anything useful, so it must fail loudly.

What this command does NOT do
-----------------------------
- It does not revoke the Anthropic API key. That is a separate kill path,
  done from the Anthropic console.
- It does not stop the Railway service. That is the third kill path,
  done from the Railway dashboard.
- It does not write to SafetyEvent. SafetyEvent is for user-triggered
  safety signals, not operator actions.

The three kill paths together
-----------------------------
1. This command (SystemConfig.maintenance_mode = True) — halts user traffic, app stays up
2. Anthropic API key revoke — kills AI features, app stays up
3. Railway service stop — kills the whole service from outside

Pick the right path for the situation. Most incidents only need #1.
"""

import logging

from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Toggle the Companion OS kill switch (maintenance mode) without admin login."

    def add_arguments(self, parser):
        parser.add_argument(
            "action",
            choices=["on", "off", "status"],
            help=(
                "on  = enable maintenance mode (halt user traffic). "
                "off = disable maintenance mode (restore traffic). "
                "status = show current state, no change."
            ),
        )
        parser.add_argument(
            "--message",
            type=str,
            default=None,
            help="Optional custom maintenance message shown to users. Only applied with 'on'.",
        )
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Skip the confirmation prompt (for scripted or non-interactive use).",
        )

    def handle(self, *args, **options):
        # Import inside handle() so manage.py introspection does not fail
        # if migrations have not run yet.
        from apps.safety.models import SystemConfig

        action = options["action"]
        message = options["message"]
        skip_confirm = options["yes"]

        try:
            config = SystemConfig.get()
        except DatabaseError as e:
            raise CommandError(f"Database error: cannot read SystemConfig. {e}")

        if action == "status":
            self._print_status(config)
            return

        if action == "on":
            if not skip_confirm:
                self.stdout.write("")
                self.stdout.write(self.style.WARNING(
                    "You are about to turn the kill switch ON."
                ))
                self.stdout.write("This halts all user-facing traffic immediately.")
                self.stdout.write("Admins reach /admin/ as normal (kill switch exempts it).")
                self.stdout.write("Use 'kill_switch off' to restore access.")
                self.stdout.write("")
                confirm = input("Type 'YES' to confirm: ").strip()
                if confirm != "YES":
                    self.stdout.write(self.style.NOTICE("Cancelled. Kill switch unchanged."))
                    return

            config.maintenance_mode = True
            if message:
                config.maintenance_message = message
            config.save()

            logger.warning(
                "Kill switch toggled ON via management command. "
                "Message: %r",
                config.maintenance_message,
            )

            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("Kill switch is now: ON"))
            self.stdout.write(f'   Message shown to users: "{config.maintenance_message}"')
            self.stdout.write(f"   Updated at (UTC): {config.updated_at.isoformat()}")
            self.stdout.write("")
            self.stdout.write("To restore access:  python manage.py kill_switch off")
            return

        if action == "off":
            was_on = config.maintenance_mode
            config.maintenance_mode = False
            config.save()

            logger.warning(
                "Kill switch toggled OFF via management command. "
                "Previous state was %s.",
                "ON" if was_on else "already OFF",
            )

            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("Kill switch is now: OFF"))
            if was_on:
                self.stdout.write("   Companion OS is accepting traffic again.")
            else:
                self.stdout.write("   (Was already OFF — no change.)")
            self.stdout.write(f"   Updated at (UTC): {config.updated_at.isoformat()}")
            return

    def _print_status(self, config):
        self.stdout.write("")
        if config.maintenance_mode:
            self.stdout.write(self.style.ERROR("Kill switch is: ON"))
            self.stdout.write(f'   Message shown to users: "{config.maintenance_message}"')
            self.stdout.write("   Users see a 503 maintenance page with crisis helplines.")
            self.stdout.write("   /admin/ and /static/ remain accessible.")
        else:
            self.stdout.write(self.style.SUCCESS("Kill switch is: OFF"))
            self.stdout.write("   Companion OS is accepting traffic normally.")
        self.stdout.write(f"   Last updated (UTC): {config.updated_at.isoformat()}")
