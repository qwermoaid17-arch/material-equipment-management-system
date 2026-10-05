from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (SiteInventoryViewSet, TransferRequestViewSet, NotificationViewSet,
                    SiteViewSet, ItemViewSet)

router = DefaultRouter()
router.register(r'inventory', SiteInventoryViewSet, basename='inventory')
router.register(r'transfers', TransferRequestViewSet, basename='transfers')
router.register(r'notifications', NotificationViewSet, basename='notifications')
router.register(r'sites', SiteViewSet, basename='sites')
router.register(r'items', ItemViewSet, basename='items')

urlpatterns = [path('', include(router.urls))]
