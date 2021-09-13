from django.apps import AppConfig


class WmsConfig(AppConfig):
    name = 'wms'

    def ready(self):
        import wms.signals
