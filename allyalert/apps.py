from django.apps import AppConfig


class AllyalertConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "allyalert"

    def ready(self):
        # Implicitly connects the signals when the app loads
        import allyalert.signals
