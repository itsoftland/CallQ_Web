from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('configdetails', '0018_keypadcountermapping_one_per_keypad'),
    ]

    operations = [
        # Drop the stale global unique indexes that enforce uniqueness across all companies.
        # These were created by an older migration series before the model was scoped per-company.
        migrations.RunSQL(
            sql="ALTER TABLE configdetails_counterconfig DROP INDEX counter_name;",
            reverse_sql="ALTER TABLE configdetails_counterconfig ADD UNIQUE (counter_name);",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE configdetails_counterconfig DROP INDEX counter_prefix_code;",
            reverse_sql="ALTER TABLE configdetails_counterconfig ADD UNIQUE (counter_prefix_code);",
        ),
        # Add the correct per-company unique constraints.
        migrations.RunSQL(
            sql="ALTER TABLE configdetails_counterconfig ADD UNIQUE configdetails_counterconfig_company_counter_name (company_id, counter_name);",
            reverse_sql="ALTER TABLE configdetails_counterconfig DROP INDEX configdetails_counterconfig_company_counter_name;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE configdetails_counterconfig ADD UNIQUE configdetails_counterconfig_company_prefix_code (company_id, counter_prefix_code);",
            reverse_sql="ALTER TABLE configdetails_counterconfig DROP INDEX configdetails_counterconfig_company_prefix_code;",
        ),
    ]
