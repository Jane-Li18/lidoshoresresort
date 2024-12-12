from django.db import migrations, models
from django.utils.timezone import now  # Import 'now' to fix the NameError

class Migration(migrations.Migration):

    dependencies = [
        ('lidoapp', '0021_alter_amenity_amenity_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='room',
            name='created_at',
            field=models.DateTimeField(default=now),  # Use 'default' for existing rows
            preserve_default=False,
        ),
    ]
