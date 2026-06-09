from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Simplify KeypadCounterMapping: each keypad has exactly one counter in pool
    mode. Remove button_index (slot position comes from TVKeypadMapping.keypad_index),
    and update unique_together to (group, keypad) + (group, counter).
    """

    dependencies = [
        ('configdetails', '0017_pool_mode'),
    ]

    operations = [
        # Clear any existing rows before altering constraints
        migrations.RunSQL(
            sql='DELETE FROM configdetails_keypadcountermapping;',
            reverse_sql=migrations.RunSQL.noop,
        ),

        # Drop old unique constraints
        migrations.AlterUniqueTogether(
            name='keypadcountermapping',
            unique_together=set(),
        ),

        # Remove button_index field
        migrations.RemoveField(
            model_name='keypadcountermapping',
            name='button_index',
        ),

        # Apply new unique constraints: one counter per keypad per group
        migrations.AlterUniqueTogether(
            name='keypadcountermapping',
            unique_together={('group', 'keypad'), ('group', 'counter')},
        ),

        # Update ordering meta (no DDL — just Django state)
        migrations.AlterModelOptions(
            name='keypadcountermapping',
            options={
                'ordering': ['group', 'keypad'],
                'verbose_name': 'Keypad Counter Mapping',
                'verbose_name_plural': 'Keypad Counter Mappings',
            },
        ),
    ]
