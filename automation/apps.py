from django.apps import AppConfig
from .tasks import start_keep_alive_thread

class AutomationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'automation'

    def ready(self):
        start_keep_alive_thread()
