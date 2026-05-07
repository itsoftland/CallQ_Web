import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Adds GroupCounterButtonMapping: the DB truth-source for the group-wide
    sequential ASCII button index each (group, dispenser, counter) occupies.

    Unlike GroupDispenserMapping (one row per dispenser in the group),
    this table has one row per counter per dispenser per group, giving every
    physical button on every dispenser a globally unique, non-resetting index
    within its group (e.g. a 4-button dispenser occupies 4 consecutive slots).
    """

    dependencies = [
        ('configdetails', '0004_add_group_dispenser_mapping_through'),
    ]

    operations = [
        migrations.CreateModel(
            name='GroupCounterButtonMapping',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('button_index', models.CharField(
                    max_length=1,
                    help_text=(
                        "Group-wide sequential ASCII button index for this counter. "
                        "Starts at chr(0x31)='1' for the first counter in the group and "
                        "increments through the full 74-slot sequence without resetting "
                        "between dispensers. Generated via get_button_index_char()."
                    ),
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('counter', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='group_button_positions',
                    to='configdetails.counterconfig',
                )),
                ('dispenser', models.ForeignKey(
                    limit_choices_to={'device_type': 'TOKEN_DISPENSER'},
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='group_counter_button_slots',
                    to='configdetails.device',
                )),
                ('group', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='counter_button_mappings',
                    to='configdetails.groupmapping',
                )),
            ],
            options={
                'verbose_name': 'Group Counter Button Mapping',
                'verbose_name_plural': 'Group Counter Button Mappings',
                'ordering': ['group', 'button_index'],
                'unique_together': {
                    ('group', 'button_index'),  # no two counters share the same slot
                    ('group', 'counter'),        # each counter has exactly one slot per group
                },
            },
        ),
    ]
