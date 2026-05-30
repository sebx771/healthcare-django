from django.urls import path
from .views import DashboardKPIsAPIView

urlpatterns = [
    path('dashboard/kpis/', DashboardKPIsAPIView.as_view(), name='dashboard-kpis'),
]