from django.core.management.base import BaseCommand
from django.utils import timezone
from rest_api.data_entry.sample_entry_job import check_for_new_data


class Command(BaseCommand):
    help = "Start import sample job."

    def handle(self, *args, **kwargs):
        current_time = timezone.now().strftime("%H:%M:%S")
        current_date = timezone.now().strftime("%Y-%m-%d")
        self.stdout.write("It's now %s on %s" % (current_time, current_date))
        check_for_new_data()
