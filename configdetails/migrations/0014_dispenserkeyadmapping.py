from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('configdetails', '0013_add_last_reset_date_to_viptokencounter'),
    ]

    operations = [
        migrations.CreateModel(
            name='DispenserKeypadMapping',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dispenser_button_index', models.CharField(
                    default='1',
                    help_text=(
                        'ASCII button index of the dispenser slot that drives this keypad. '
                        'Mirrors GroupDispenserMapping.dispenser_button_index.'
                    ),
                    max_length=1,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('group', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='dispenser_keypad_mappings',
                    to='configdetails.groupmapping',
                )),
                ('dispenser', models.ForeignKey(
                    limit_choices_to={'device_type': 'TOKEN_DISPENSER'},
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='dkm_dispenser_slots',
                    to='configdetails.device',
                )),
                ('keypad', models.ForeignKey(
                    limit_choices_to={'device_type': 'KEYPAD'},
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='dkm_keypad_slots',
                    to='configdetails.device',
                )),
            ],
            options={
                'verbose_name': 'Dispenser to Keypad Mapping',
                'verbose_name_plural': 'Dispenser to Keypad Mappings',
                'ordering': ['group', 'dispenser', 'dispenser_button_index'],
                'unique_together': {('group', 'keypad')},
            },
        ),
    ]
