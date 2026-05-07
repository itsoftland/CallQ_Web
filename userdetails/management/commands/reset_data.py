"""
Django Management Command: Reset Database Data

This command resets all data in the database while preserving:
1. Super Admin users
2. Location data (Country, State, District)
3. Database schema (all tables remain intact)

Usage:
    python manage.py reset_data           # Runs in dry-run mode (preview)
    python manage.py reset_data --confirm # Actually deletes the data
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.sessions.models import Session

from userdetails.models import User, AppLoginHistory
from companydetails.models import (
    Country, State, District,  # These will be PRESERVED
    Company, Branch, AuthenticationLog, ActivityLog, DealerCustomer
)
from configdetails.models import (
    Device, ProductionBatch, ProductionSerialNumber,
    Mapping, ButtonMapping, DeviceConfig, TVConfig, TVAd, LedConfig
)
from licenses.models import Batch, License, BatchRequest


class Command(BaseCommand):
    help = 'Reset database data while preserving Super Admin users and location data (Country, State, District)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Actually delete the data. Without this flag, only a preview is shown.',
        )

    def handle(self, *args, **options):
        confirm = options['confirm']
        
        self.stdout.write(self.style.WARNING('\n' + '='*60))
        self.stdout.write(self.style.WARNING('DATABASE RESET UTILITY'))
        self.stdout.write(self.style.WARNING('='*60))
        
        # Show what will be preserved
        self.stdout.write(self.style.SUCCESS('\n✓ WILL BE PRESERVED:'))
        
        super_admins = User.objects.filter(role=User.Role.SUPER_ADMIN)
        countries = Country.objects.all()
        states = State.objects.all()
        districts = District.objects.all()
        
        self.stdout.write(f'  - Super Admin users: {super_admins.count()}')
        for admin in super_admins:
            self.stdout.write(f'    • {admin.username} ({admin.email})')
        
        self.stdout.write(f'  - Countries: {countries.count()}')
        self.stdout.write(f'  - States: {states.count()}')
        self.stdout.write(f'  - Districts: {districts.count()}')
        
        # Show what will be deleted
        self.stdout.write(self.style.ERROR('\n✗ WILL BE DELETED:'))
        
        # Users (except Super Admins)
        users_to_delete = User.objects.exclude(role=User.Role.SUPER_ADMIN)
        self.stdout.write(f'  - Users (non-Super Admin): {users_to_delete.count()}')
        
        # User details
        app_login_history = AppLoginHistory.objects.all()
        self.stdout.write(f'  - App Login History: {app_login_history.count()}')
        
        # Company details
        companies = Company.objects.all()
        branches = Branch.objects.all()
        auth_logs = AuthenticationLog.objects.all()
        activity_logs = ActivityLog.objects.all()
        dealer_customers = DealerCustomer.objects.all()
        
        self.stdout.write(f'  - Companies: {companies.count()}')
        self.stdout.write(f'  - Branches: {branches.count()}')
        self.stdout.write(f'  - Authentication Logs: {auth_logs.count()}')
        self.stdout.write(f'  - Activity Logs: {activity_logs.count()}')
        self.stdout.write(f'  - Dealer Customers: {dealer_customers.count()}')
        
        # Config details
        devices = Device.objects.all()
        production_batches = ProductionBatch.objects.all()
        production_serials = ProductionSerialNumber.objects.all()
        mappings = Mapping.objects.all()
        button_mappings = ButtonMapping.objects.all()
        device_configs = DeviceConfig.objects.all()
        tv_configs = TVConfig.objects.all()
        tv_ads = TVAd.objects.all()
        led_configs = LedConfig.objects.all()
        
        self.stdout.write(f'  - Devices: {devices.count()}')
        self.stdout.write(f'  - Production Batches: {production_batches.count()}')
        self.stdout.write(f'  - Production Serial Numbers: {production_serials.count()}')
        self.stdout.write(f'  - Mappings: {mappings.count()}')
        self.stdout.write(f'  - Button Mappings: {button_mappings.count()}')
        self.stdout.write(f'  - Device Configs: {device_configs.count()}')
        self.stdout.write(f'  - TV Configs: {tv_configs.count()}')
        self.stdout.write(f'  - TV Ads: {tv_ads.count()}')
        self.stdout.write(f'  - LED Configs: {led_configs.count()}')
        
        # Licenses
        license_batches = Batch.objects.all()
        licenses = License.objects.all()
        batch_requests = BatchRequest.objects.all()
        
        self.stdout.write(f'  - License Batches: {license_batches.count()}')
        self.stdout.write(f'  - Licenses: {licenses.count()}')
        self.stdout.write(f'  - Batch Requests: {batch_requests.count()}')
        
        # Sessions
        sessions = Session.objects.all()
        self.stdout.write(f'  - Sessions: {sessions.count()}')
        
        if not confirm:
            self.stdout.write(self.style.WARNING('\n' + '='*60))
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No data was deleted!'))
            self.stdout.write(self.style.WARNING('To actually delete, run with --confirm flag:'))
            self.stdout.write(self.style.HTTP_INFO('  python manage.py reset_data --confirm'))
            self.stdout.write(self.style.WARNING('='*60 + '\n'))
            return
        
        # Confirmation prompt
        self.stdout.write(self.style.WARNING('\n' + '='*60))
        self.stdout.write(self.style.ERROR('⚠️  WARNING: This action is IRREVERSIBLE!'))
        self.stdout.write(self.style.WARNING('='*60))
        
        user_input = input('\nType "DELETE" to confirm: ')
        if user_input != 'DELETE':
            self.stdout.write(self.style.ERROR('Aborted. No data was deleted.'))
            return
        
        # Perform the deletion
        self.stdout.write(self.style.HTTP_INFO('\nDeleting data...'))
        
        try:
            with transaction.atomic():
                # Delete in order to respect foreign key constraints
                
                # 1. Sessions first
                Session.objects.all().delete()
                self.stdout.write('  ✓ Deleted all sessions')
                
                # 2. License related
                License.objects.all().delete()
                self.stdout.write('  ✓ Deleted all licenses')
                
                BatchRequest.objects.all().delete()
                self.stdout.write('  ✓ Deleted all batch requests')
                
                Batch.objects.all().delete()
                self.stdout.write('  ✓ Deleted all license batches')
                
                # 3. Config related (most dependent first)
                TVAd.objects.all().delete()
                self.stdout.write('  ✓ Deleted TV ads')
                
                TVConfig.objects.all().delete()
                self.stdout.write('  ✓ Deleted TV configs')
                
                LedConfig.objects.all().delete()
                self.stdout.write('  ✓ Deleted LED configs')
                
                DeviceConfig.objects.all().delete()
                self.stdout.write('  ✓ Deleted device configs')
                
                ButtonMapping.objects.all().delete()
                self.stdout.write('  ✓ Deleted button mappings')
                
                Mapping.objects.all().delete()
                self.stdout.write('  ✓ Deleted mappings')
                
                Device.objects.all().delete()
                self.stdout.write('  ✓ Deleted devices')
                
                ProductionSerialNumber.objects.all().delete()
                self.stdout.write('  ✓ Deleted production serial numbers')
                
                ProductionBatch.objects.all().delete()
                self.stdout.write('  ✓ Deleted production batches')
                
                # 4. User login history
                AppLoginHistory.objects.all().delete()
                self.stdout.write('  ✓ Deleted app login history')
                
                # 5. Activity logs
                ActivityLog.objects.all().delete()
                self.stdout.write('  ✓ Deleted activity logs')
                
                AuthenticationLog.objects.all().delete()
                self.stdout.write('  ✓ Deleted authentication logs')
                
                # 6. Dealer customers (before users, as users might reference)
                DealerCustomer.objects.all().delete()
                self.stdout.write('  ✓ Deleted dealer customers')
                
                # 7. Users (except Super Admins)
                User.objects.exclude(role=User.Role.SUPER_ADMIN).delete()
                self.stdout.write('  ✓ Deleted non-Super Admin users')
                
                # 8. Branches
                Branch.objects.all().delete()
                self.stdout.write('  ✓ Deleted branches')
                
                # 9. Companies
                Company.objects.all().delete()
                self.stdout.write('  ✓ Deleted companies')
                
                self.stdout.write(self.style.SUCCESS('\n' + '='*60))
                self.stdout.write(self.style.SUCCESS('✓ DATABASE RESET COMPLETED SUCCESSFULLY!'))
                self.stdout.write(self.style.SUCCESS('='*60))
                self.stdout.write(self.style.SUCCESS('\nPreserved:'))
                self.stdout.write(f'  - Super Admin users: {User.objects.filter(role=User.Role.SUPER_ADMIN).count()}')
                self.stdout.write(f'  - Countries: {Country.objects.count()}')
                self.stdout.write(f'  - States: {State.objects.count()}')
                self.stdout.write(f'  - Districts: {District.objects.count()}')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Error during deletion: {str(e)}'))
            self.stdout.write(self.style.ERROR('Transaction rolled back. No data was deleted.'))
            raise CommandError(f'Reset failed: {str(e)}')
