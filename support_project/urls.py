from django.contrib import admin
from django.urls import path
from support_system import views

urlpatterns = [
    # Админ-панель Django
    path('admin/', admin.site.urls),
    
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('notifications/', views.notifications, name='notifications'),
    
    # Заявки пользователей
    path('tickets/', views.user_tickets, name='user_tickets'),
    path('tickets/create/', views.create_ticket, name='create_ticket'),
    path('tickets/<int:ticket_id>/', views.ticket_detail, name='ticket_detail'),
    path('tickets/<int:ticket_id>/reply/', views.reply_ticket, name='reply_ticket'),
    path('tickets/<int:ticket_id>/status/', views.update_ticket_status, name='update_ticket_status'),
    
    # Страницы специалистов поддержки
    path('support/', views.support_tickets, name='support_tickets'),
    path('support/new/', views.support_tickets, {'filter': 'new'}, name='new_tickets'),
    path('support/awaiting/', views.support_tickets, {'filter': 'awaiting'}, name='awaiting_response'),
    path('support/take/<int:ticket_id>/', views.take_ticket, name='take_ticket'),
    
    # FAQ и база знаний
    path('faq/', views.faq, name='faq'),
    path('knowledge-base/', views.knowledge_base, name='knowledge_base'),
    path('knowledge-base/<int:article_id>/', views.knowledge_base_article, name='knowledge_base_article'),
]