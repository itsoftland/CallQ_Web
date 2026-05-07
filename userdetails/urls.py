from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:pk>/delete/', views.user_delete, name='user_delete'),
    path('users/<int:pk>/toggle/', views.user_toggle_status, name='user_toggle_status'),
    path('api/android/Androidlogin', views.android_config_login, name='android_config_login'),
    path('api/android/getDeviceByCustomer', views.getDeviceByCustomer, name='getDeviceByCustomer'),
    path('app/login-history/', views.app_login_history, name='app_login_history'),
    path('profile/', views.profile, name='profile'),
    path('trigger-password-reset/', views.trigger_password_reset, name='trigger_password_reset'),
    
    # Password Reset
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='userdetails/password_reset.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='userdetails/password_reset_done.html'), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='userdetails/password_reset_confirm.html'), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(template_name='userdetails/password_reset_complete.html'), name='password_reset_complete'),
]
