from django.db import models

# Create your models here.
class BaseModel(models.Model):
	class Meta:
		abstract = True
	def __str__(self):
		pass
    

class BaseOrder(models.Model):

    class Meta:
        abstract = True

    def __str__(self):
        pass
    
class BaseCart(models.Model):

    class Meta:
        abstract = True

    def __str__(self):
        pass

class BaseShipment(models.Model):

    class Meta:
        abstract = True

    def __str__(self):
        pass
    
class Return(models.Model):

    class Meta:
        abstract = True

    def __str__(self):
        pass
    