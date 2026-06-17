from django.db import migrations


def deduplicate_branch_names(apps, schema_editor):
    """
    Before adding unique_together (company, branch_name), rename any duplicate
    branch names within the same company so the constraint can be applied safely.
    Duplicates are renamed by appending a counter: "Main Branch (2)", etc.
    """
    Branch = apps.get_model('companydetails', 'Branch')

    # Group by (company_id, branch_name) and find duplicates
    from collections import defaultdict
    groups = defaultdict(list)
    for branch in Branch.objects.order_by('company_id', 'branch_name', 'id'):
        groups[(branch.company_id, branch.branch_name)].append(branch)

    for (company_id, branch_name), branches in groups.items():
        if len(branches) <= 1:
            continue
        # Keep the first (oldest id) intact; rename the rest
        for idx, branch in enumerate(branches[1:], start=2):
            new_name = f"{branch_name} ({idx})"
            # Resolve any collision with the new name too
            while Branch.objects.filter(company_id=company_id, branch_name=new_name).exists():
                idx += 1
                new_name = f"{branch_name} ({idx})"
            branch.branch_name = new_name
            branch.save()


def noop(apps, schema_editor):
    pass  # deduplication is not reversible, but constraint removal is safe


class Migration(migrations.Migration):

    dependencies = [
        ('companydetails', '0003_add_noof_config_apk'),
    ]

    operations = [
        # Step 1: clean up any existing duplicates before applying the constraint
        migrations.RunPython(deduplicate_branch_names, reverse_code=noop),
        # Step 2: add the unique constraint
        migrations.AlterUniqueTogether(
            name='branch',
            unique_together={('company', 'branch_name')},
        ),
    ]
