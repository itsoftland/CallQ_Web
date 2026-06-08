from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('configdetails', '0015_mqtttokenlog'),
    ]

    operations = [
        migrations.AddField(
            model_name='tvconfig',
            name='is_offline',
            field=models.BooleanField(default=False),
        ),
    ]
