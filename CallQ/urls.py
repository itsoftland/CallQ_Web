from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from companydetails import views
from configdetails import views as config_views
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(url='/CallQ/', permanent=True)),
    path('CallQ/', include([
        path('admin/', admin.site.urls),
        path('', include('companydetails.urls')),
        path('config/', include('configdetails.urls')),
        path('auth/', include('userdetails.urls')),
        path('licenses/', include('licenses.urls')),

        # Token Dispenser Configuration API (at root level)
        path('api/token-dispenser/config', config_views.get_token_dispenser_config_api, name='get_token_dispenser_config_api'),
        # Counter Swap API (at root level)
        path('api/counters/swap', config_views.swap_counters_api, name='swap_counters_api'),
        # Token Report API (at root level)
        path('api/external/token-report', config_views.token_report_api, name='token_report_api'),
        # Android APK Mapped Counters API (at root level)
        path('api/android/mapped-counters', config_views.get_android_mapped_counters, name='get_android_mapped_counters'),


        path('login/', views.CustomLoginView.as_view(), name='login'),
        path('logout/', auth_views.LogoutView.as_view(), name='logout'),
        
        # Override password reset views to hide sidebar
        path('accounts/password_reset/', views.CustomPasswordResetView.as_view(extra_context={'hide_sidebar': True}), name='password_reset'),
        path('accounts/password_reset/done/', auth_views.PasswordResetDoneView.as_view(extra_context={'hide_sidebar': True}), name='password_reset_done'),
        path('accounts/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(extra_context={'hide_sidebar': True}), name='password_reset_confirm'),
        path('accounts/reset/done/', auth_views.PasswordResetCompleteView.as_view(extra_context={'hide_sidebar': True}), name='password_reset_complete'),

        # Note: auth/logout is deprecated in Django 5.x as GET, all templates must use POST to 'logout' name.
    ])),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
