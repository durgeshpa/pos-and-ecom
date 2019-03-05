from django.db import migrations, models
from django.contrib.postgres.operations import TrigramExtension

class Migration(migrations.Migration):
    operations = [
        TrigramExtension(),
    ]