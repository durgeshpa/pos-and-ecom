from django.db.models import Manager

class EcomTripModelManager(Manager):

    def get_queryset(self):
        return super().get_queryset().filter(trip_type='ECOM')