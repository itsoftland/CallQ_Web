from django.contrib import admin
from .models import User, AppLoginHistory

@admin.register(AppLoginHistory)
class AppLoginHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'company', 'mac_address', 'version', 'timestamp')
    list_filter = ('company', 'version', 'timestamp')
    search_fields = ('user__email', 'user__username', 'mac_address')
    readonly_fields = ('timestamp',)

# You might also want to register the custom User model if not already done
# admin.site.register(User)
