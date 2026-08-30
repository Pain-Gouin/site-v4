from django.core.management.base import BaseCommand
from imagekit.utils import get_cache


class Command(BaseCommand):
    help = (
        "Clear the ImageKit cache backend "
        "(does not delete generated files on disk, just the cache-backend records tracking them)."
    )

    def handle(self, *args, **options):
        cache = get_cache()
        cache.clear()
        self.stdout.write(self.style.SUCCESS("ImageKit cache cleared successfully."))
