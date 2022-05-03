from django.apps import AppConfig


class ShopsConfig(AppConfig):
    name = 'shops'

    def ready(self):
        import shops.signals