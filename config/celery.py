import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("parsepro")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# NOTE: Do NOT manually call eventlet.monkey_patch() here!
# When you use `celery -A config worker -P eventlet`, Celery handles
# the monkey patching automatically at the right time.
# Manual patching here breaks Django's database thread-local connections.

