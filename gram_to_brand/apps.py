from django.apps import AppConfig


class GramToBrandConfig(AppConfig):
    name = 'gram_to_brand'
    verbose_name = 'gram_to_brand'

    def ready(self):
        import gram_to_brand.signals