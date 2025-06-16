from django.urls import path
from . import api_views

urlpatterns = [
    path('tickets/', api_views.TicketListCreateView.as_view(), name='api-ticket-list'),
    path('tickets/<int:pk>/', api_views.TicketDetailView.as_view(), name='api-ticket-detail'),
    path('tickets/<int:ticket_id>/messages/', api_views.TicketMessageListCreateView.as_view(), name='api-ticket-messages'),
    path('support-users/', api_views.SupportUserListView.as_view(), name='api-support-user-list'),
    path('users/', api_views.UserListView.as_view(), name='api-user-list'),
] 