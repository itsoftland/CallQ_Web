import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Converts GroupMapping.dispensers from a plain M2M to a through-model M2M
    (GroupDispenserMapping) that stores a per-dispenser button index.

    Safe for both fresh databases (table doesn't exist yet) and upgraded
    databases (table may already exist from a previous partial run).

    Steps:
      1. Create the configdetails_groupdispensermapping table (real CreateModel).
      2. If the old implicit join table exists, migrate its rows into the new
         through table with sequential ASCII button indices, then drop it.
      3. Update Django ORM state so dispensers uses the through model.
    """

    dependencies = [
        ('configdetails', '0003_tokenreport'),
    ]

    operations = [

        # ── Step 1: Create the through-model table ────────────────────────────
        # Use a real CreateModel so fresh databases get the table created.
        # On databases where it already exists this will raise an error, so we
        # guard it with SeparateDatabaseAndState + RunSQL CREATE IF NOT EXISTS.
        migrations.RunSQL(
            sql="""
                CREATE TABLE IF NOT EXISTS configdetails_groupdispensermapping (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    dispenser_button_index VARCHAR(1) NOT NULL DEFAULT '1',
                    created_at DATETIME(6) NOT NULL,
                    dispenser_id BIGINT NOT NULL,
                    group_id BIGINT NOT NULL,
                    UNIQUE KEY uq_group_dispenser (group_id, dispenser_id),
                    UNIQUE KEY uq_group_button (group_id, dispenser_button_index),
                    CONSTRAINT fk_gdm_dispenser FOREIGN KEY (dispenser_id)
                        REFERENCES configdetails_device (id) ON DELETE CASCADE,
                    CONSTRAINT fk_gdm_group FOREIGN KEY (group_id)
                        REFERENCES configdetails_groupmapping (id) ON DELETE CASCADE
                );
            """,
            reverse_sql="DROP TABLE IF EXISTS configdetails_groupdispensermapping;",
        ),

        # Tell Django ORM state that GroupDispenserMapping now exists.
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name='GroupDispenserMapping',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('dispenser_button_index', models.CharField(
                            default='1',
                            help_text=(
                                "Physical button position for this dispenser within the group. "
                                "ASCII character: '1' (slot 1) through 'z' (slot 74). "
                                "Generated via get_button_index_char()."
                            ),
                            max_length=1,
                        )),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('dispenser', models.ForeignKey(
                            limit_choices_to={'device_type': 'TOKEN_DISPENSER'},
                            on_delete=django.db.models.deletion.CASCADE,
                            related_name='group_dispenser_slots',
                            to='configdetails.device',
                        )),
                        ('group', models.ForeignKey(
                            on_delete=django.db.models.deletion.CASCADE,
                            related_name='dispenser_slot_mappings',
                            to='configdetails.groupmapping',
                        )),
                    ],
                    options={
                        'verbose_name': 'Group Dispenser Mapping',
                        'verbose_name_plural': 'Group Dispenser Mappings',
                        'ordering': ['group', 'dispenser_button_index'],
                        'unique_together': {('group', 'dispenser'), ('group', 'dispenser_button_index')},
                    },
                ),
            ],
        ),

        # ── Step 2: Migrate existing rows (only if the old table exists) ───────
        # Assign sequential ASCII button indices ('1', '2', …) per group.
        # The INSERT is wrapped in an IF so it silently no-ops on fresh DBs
        # where configdetails_groupmapping_dispensers was never created.
        migrations.RunSQL(
            sql="""
                SET @old_table_exists = (
                    SELECT COUNT(*)
                    FROM information_schema.tables
                    WHERE table_schema = DATABASE()
                      AND table_name = 'configdetails_groupmapping_dispensers'
                );

                SET @migrate_sql = IF(
                    @old_table_exists > 0,
                    'INSERT INTO configdetails_groupdispensermapping
                         (group_id, dispenser_id, dispenser_button_index, created_at)
                     SELECT
                         groupmapping_id,
                         device_id,
                         CHAR(48 + ROW_NUMBER() OVER (
                             PARTITION BY groupmapping_id ORDER BY device_id
                         )),
                         NOW()
                     FROM configdetails_groupmapping_dispensers
                     WHERE NOT EXISTS (
                         SELECT 1 FROM configdetails_groupdispensermapping gdm
                         WHERE gdm.group_id = configdetails_groupmapping_dispensers.groupmapping_id
                           AND gdm.dispenser_id = configdetails_groupmapping_dispensers.device_id
                     )',
                    'SELECT 1'
                );

                PREPARE stmt FROM @migrate_sql;
                EXECUTE stmt;
                DEALLOCATE PREPARE stmt;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),

        # ── Step 3: Drop the old implicit join table (if it exists) ───────────
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS configdetails_groupmapping_dispensers;",
            reverse_sql="""
                CREATE TABLE configdetails_groupmapping_dispensers (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    groupmapping_id BIGINT NOT NULL,
                    device_id BIGINT NOT NULL,
                    UNIQUE KEY unique_group_device (groupmapping_id, device_id)
                );
            """,
        ),

        # ── Step 4: Update Django state: dispensers now uses through model ─────
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name='groupmapping',
                    name='dispensers',
                    field=models.ManyToManyField(
                        blank=True,
                        limit_choices_to={'device_type': 'TOKEN_DISPENSER'},
                        related_name='group_dispensers',
                        through='configdetails.GroupDispenserMapping',
                        to='configdetails.device',
                    ),
                ),
            ],
        ),
    ]

