from django.apps import AppConfig


class TribunaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tribuna'

    def ready(self):
        from . import signals