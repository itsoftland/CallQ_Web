import os
import django

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CallQ.settings')
    django.setup()

    from django.db import connection
    from django.apps import apps

    with connection.cursor() as cursor:
        table_names = connection.introspection.table_names(cursor)

    with connection.schema_editor() as schema_editor:
        for model in apps.get_models(include_auto_created=True):
            # Only process models that are managed by Django
            if model._meta.managed and not model._meta.proxy:
                table_name = model._meta.db_table
                
                if table_name in table_names:
                    with connection.cursor() as cursor:
                        try:
                            desc = connection.introspection.get_table_description(cursor, table_name)
                            columns = [col.name for col in desc]
                        except Exception as e:
                            print(f"Could not introspect {table_name}: {e}")
                            continue
                    
                    for field in model._meta.local_fields:
                        if field.column and field.column not in columns:
                            print(f"Adding column {field.column} to {table_name}...")
                            try:
                                # For NOT NULL fields without defaults, schema_editor might fail on populated tables
                                # If it does, we might need a workaround, but let's try the standard way first.
                                schema_editor.add_field(model, field)
                                print(f"Successfully added {field.column} to {table_name}")
                            except Exception as e:
                                print(f"Error adding {field.column} to {table_name}: {e}")
                else:
                    print(f"Creating table {table_name}...")
                    try:
                        schema_editor.create_model(model)
                        print(f"Successfully created table {table_name}")
                    except Exception as e:
                        print(f"Error creating table {table_name}: {e}")

if __name__ == '__main__':
    main()
