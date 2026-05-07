import os
import django
from django.contrib.auth import get_user_model

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CallQ.settings')
django.setup()

User = get_user_model()
username = 'audit_admin'
email = 'audit@example.com'
password = 'audit_password_123'

if not User.objects.filter(username=username).exists():
    print(f"Creating superuser {username}...")
    User.objects.create_superuser(username=username, email=email, password=password, role='SUPER_ADMIN')
    print("Superuser created.")
else:
    print(f"Superuser {username} already exists.")
