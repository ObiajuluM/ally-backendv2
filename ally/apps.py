from django.apps import AppConfig


class AllyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ally"

    def ready(self):
        # Implicitly connects the signals when the app loads
        import ally.signals
