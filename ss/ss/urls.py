# هذا الملف يستبدل ss/urls.py (ملف urls.py الرئيسي للمشروع)
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from syst import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('syst.urls')),
    path('api-auth/', include('rest_framework.urls')),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', views.dashboard_view, name='dashboard'),
    path('dashboard/', views.dashboard_view),
    path('inventory/', views.inventory_page, name='inventory'),
    path('transfers/', views.transfers_page, name='transfers'),
    path('notifications/', views.notifications_page, name='notifications'),
]
