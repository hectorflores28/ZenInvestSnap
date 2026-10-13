import time
from datetime import datetime, time as datetime_time, timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from main.utils import perform_snapshot


class Command(BaseCommand):
    help = 'Runs the daily snapshot for all users.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--daily',
            action='store_true',
            help='Wait for midnight in the configured Django timezone and run daily.',
        )

    def handle(self, *args, **options):
        if options['daily']:
            while True:
                now = timezone.localtime()
                seconds_until_run = self.seconds_until_next_run(now)
                next_run = now + timedelta(seconds=seconds_until_run)
                self.stdout.write(
                    f'Next daily snapshot at {timezone.localtime(next_run).isoformat()}'
                )
                time.sleep(seconds_until_run)
                self.run_snapshots()
        else:
            self.run_snapshots()

    @staticmethod
    def seconds_until_next_run(now):
        next_day = now.date() + timedelta(days=1)
        next_run = timezone.make_aware(
            datetime.combine(next_day, datetime_time.min),
            now.tzinfo,
        )
        return max(0, (next_run - now).total_seconds())

    def run_snapshots(self):
        self.stdout.write("Starting daily snapshot for all users...")
        users = User.objects.all()
        for user in users:
            self.stdout.write(f"Processing user: {user.username}")
            perform_snapshot(user)
        self.stdout.write(self.style.SUCCESS("Daily snapshot completed for all users."))
