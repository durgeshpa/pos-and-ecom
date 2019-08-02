from django.apps import AppConfig


class NotificationCenterConfig(AppConfig):
    name = 'notification_center'
    verbose_name = 'Notification Center'

    def ready(self):
        import notification_center.utils
        import notification_center.signals
