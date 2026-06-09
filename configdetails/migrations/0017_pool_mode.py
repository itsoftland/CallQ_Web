from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('configdetails', '0016_tvconfig_is_offline'),
    ]

    operations = [
        # Part 1: add pool_mode to GroupMapping
        migrations.AddField(
            model_name='groupmapping',
            name='pool_mode',
            field=models.BooleanField(
                default=False,
                help_text='Pool mode enables keypad-based counter mapping.',
            ),
        ),

        # Part 2: create KeypadCounterMapping table
        migrations.CreateModel(
            name='KeypadCounterMapping',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('button_index', models.CharField(
                    max_length=1,
                    help_text=(
                        "Slot position for this counter in the TV response (1-8). "
                        "ASCII character: chr(0x31)='1' through chr(0x38)='8'."
                    ),
                )),
                ('group', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='keypad_counter_mappings',
                    to='configdetails.groupmapping',
                )),
                ('keypad', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='pool_counter_mappings',
                    limit_choices_to={'device_type': 'KEYPAD'},
                    to='configdetails.device',
                )),
                ('counter', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='pool_keypad_positions',
                    to='configdetails.counterconfig',
                )),
            ],
            options={
                'verbose_name': 'Keypad Counter Mapping',
                'verbose_name_plural': 'Keypad Counter Mappings',
                'ordering': ['group', 'button_index'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='keypadcountermapping',
            unique_together={('group', 'button_index'), ('group', 'counter')},
        ),
    ]
