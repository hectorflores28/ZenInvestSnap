from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from main.utils import perform_snapshot

class Command(BaseCommand):
    help = 'Runs the daily snapshot for all users.'

    def handle(self, *args, **options):
        self.stdout.write("Starting daily snapshot for all users...")
        users = User.objects.all()
        for user in users:
            self.stdout.write(f"Processing user: {user.username}")
            perform_snapshot(user)
        self.stdout.write(self.style.SUCCESS("Daily snapshot completed for all users."))
