from django.urls import path
from . import views

urlpatterns = [
    path('', views.reports_dashboard, name='reports_dashboard'),
    path('generate/tickets/', views.generate_tickets_report, name='generate_tickets_report'),
    path('generate/support/', views.generate_support_report, name='generate_support_report'),
    path('generate/users/', views.generate_users_report, name='generate_users_report'),
    path('export/<int:report_id>/', views.export_report, name='export_report'),
] 