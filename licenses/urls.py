from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import BatchViewSet, LicenseViewSet

router = DefaultRouter()
router.register(r'batches', BatchViewSet, basename='batch')
router.register(r'licenses', LicenseViewSet, basename='license')

urlpatterns = [
    path('', include(router.urls)),
    path('list/', views.batch_page, name='batch_list'),
    path('purchase/', views.purchase_batch, name='purchase_batch'),
    path('approve/<int:batch_id>/', views.approve_batch, name='approve_batch'),
    path('download/<int:batch_id>/', views.batch_download, name='batch_download'),
    
    # Batch Request URLs
    path('request/', views.request_batch, name='request_batch'),
    path('requests/', views.batch_requests_list, name='batch_requests_list'),
    path('requests/approve/<int:request_id>/', views.approve_batch_request, name='approve_batch_request'),
    path('requests/reject/<int:request_id>/', views.reject_batch_request, name='reject_batch_request'),
]
