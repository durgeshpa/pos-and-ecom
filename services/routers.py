from django.db import DEFAULT_DB_ALIAS

class AnalyticsRouter:
    """
    A router to control all database operations on models in the
    services application.
    """
    def db_for_read(self, model, **hints):
        """
        Attempts to read auth models go to gfanalytics.
        """
        if model._meta.app_label == 'services':
            return 'data'
        return None

    def db_for_write(self, model, **hints):
        """
        Attempts to write services models go to gfanalytics.
        """
        if model._meta.app_label == 'services':
            return 'data'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if a model in the services app is involved.
        """
        if obj1._meta.app_label == 'services' or \
           obj2._meta.app_label == 'services':
           return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Make sure the services app only appears in the 'gfanalytics'
        database.
        """
        if app_label == 'services':
            return db == 'data'
        return None
