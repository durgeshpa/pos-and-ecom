from django.apps import AppConfig


class RetailerToSpConfig(AppConfig):
    name = 'retailer_to_sp'

    def ready(self):
        import retailer_to_sp.signals
