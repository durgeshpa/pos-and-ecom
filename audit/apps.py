from django.apps import AppConfig


class AuditConfig(AppConfig):
    name = 'audit'

    def ready(self):
        import audit.signals
