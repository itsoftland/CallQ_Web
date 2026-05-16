import os
import sys
import django
from django.core.management import call_command

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CallQ.settings')
django.setup()

print("Running migrations internally...")
try:
    call_command('migrate', 'configdetails')
    print("Migration successful.")
except Exception as e:
    print("Error:", e)
