from django.apps import AppConfig


class PosConfig(AppConfig):
    name = 'pos'
    verbose_name = 'Point Of Sale'

    def ready(self):
        import pos.signals
