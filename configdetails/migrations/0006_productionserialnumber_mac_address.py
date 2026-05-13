from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('configdetails', '0005_groupcounterbuttonmapping'),
    ]

    operations = [
        migrations.AddField(
            model_name='productionserialnumber',
            name='mac_address',
            field=models.CharField(
                blank=True,
                help_text='Physical MAC address of the device (optional)',
                max_length=100,
                null=True,
            ),
        ),
    ]
