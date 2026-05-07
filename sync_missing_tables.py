import os
import django
from django.db import connection, utils

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CallQ.settings')
django.setup()

from django.core.management import call_command
from io import StringIO

def create_missing_tables():
    apps = ['companydetails', 'configdetails', 'licenses', 'userdetails']
    migrations = ['0001', '0002']
    
    with connection.cursor() as cursor:
        for app in apps:
            for mig in migrations:
                out = StringIO()
                try:
                    call_command('sqlmigrate', app, mig, stdout=out)
                except Exception as e:
                    continue
                    
                sql_statements = out.getvalue().split(';')
                
                for statement in sql_statements:
                    stmt = statement.strip()
                    if not stmt:
                        continue
                    if stmt.startswith('--'):
                        lines = [line for line in stmt.split('\n') if not line.strip().startswith('--')]
                        stmt = '\n'.join(lines).strip()
                        if not stmt:
                            continue
                            
                    try:
                        cursor.execute(stmt)
                        print(f"Executed: {stmt[:50]}...")
                    except utils.OperationalError as e:
                        if e.args[0] in (1050, 1060, 1061, 1062, 1091):
                            pass # ignore
                        else:
                            print(f"OperationalError executing {stmt[:50]}... : {e}")
                    except Exception as e:
                        # Ignore other potential issues like duplicate indexes (e.args[0] might be different)
                        pass

if __name__ == "__main__":
    create_missing_tables()
